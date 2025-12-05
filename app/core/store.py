import os
from pathlib import Path
from typing import Dict, Any, Optional

from sqlmodel import SQLModel, Field, Session, create_engine, select
from datetime import datetime
from typing import List
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _strip_quotes(value: str) -> str:
    """Remove surrounding single or double quotes from a value."""
    if isinstance(value, str) and len(value) >= 2:
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
    return value


class EnvStore:
    """Simple wrapper around the existing .env file format."""

    def __init__(self, path: Path | str = None):
        self.path = Path(path) if path is not None else PROJECT_ROOT.parent / ".env"

    def read_all(self) -> Dict[str, str]:
        vals: Dict[str, str] = {}
        if not self.path.exists():
            return vals
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = _strip_quotes(v.strip())
        return vals

    def write_many(self, updates: Dict[str, Any]) -> None:
        current = self.read_all()
        for k, v in updates.items():
            current[k] = str(v)
        lines = [f"{k}={v}" for k, v in current.items()]
        self.path.write_text("\n".join(lines), encoding="utf-8")


class LegacySetting(SQLModel, table=True):
    """Legacy simple key/value table used previously.

    We keep this model so we can detect and migrate old data into the
    richer `ConfigEntry` schema.
    """
    key: str = Field(primary_key=True)
    value: str


class ConfigEntry(SQLModel, table=True):
    """Richer configuration schema for settings.

    Columns:
    - key: primary key string identifier for the setting (e.g. LOG_LEVEL)
    - value: stored as text (stringified)
    - value_type: textual tag for the type (e.g. 'str', 'int', 'bool')
    - description: optional human-readable description
    - is_immutable: prevents admin API from changing the value
    - created_at, updated_at: timestamps
    """

    key: str = Field(primary_key=True)
    value: str
    value_type: str = Field(default="str")
    description: Optional[str] = None
    is_immutable: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DBStore:
    """SQLModel/SQLite-backed key/value store for settings."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else PROJECT_ROOT.parent / "settings.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{self.db_path}", echo=False, connect_args={"check_same_thread": False})
        # Create tables if missing
        SQLModel.metadata.create_all(self._engine)
        # Run lightweight migrations (add columns / migrate legacy data)
        self._ensure_migrations()

    def read_all(self) -> Dict[str, str]:
        with Session(self._engine) as sess:
            statement = select(ConfigEntry)
            results = sess.exec(statement).all()
            return {r.key: _strip_quotes(r.value) for r in results}

    def write_many(self, updates: Dict[str, Any]) -> None:
        with Session(self._engine) as sess:
            for k, v in updates.items():
                now = datetime.utcnow()
                # Preserve existing entry attributes if present
                existing = sess.get(ConfigEntry, k)
                if existing:
                    if existing.is_immutable:
                        # skip immutable entries
                        continue
                    existing.value = str(v)
                    existing.updated_at = now
                    sess.add(existing)
                else:
                    entry = ConfigEntry(key=k, value=str(v), value_type="str", created_at=now, updated_at=now)
                    sess.add(entry)
            sess.commit()

    def is_empty(self) -> bool:
        with Session(self._engine) as sess:
            statement = select(ConfigEntry).limit(1)
            res = sess.exec(statement).first()
            return res is None

    def _ensure_migrations(self) -> None:
        """Run lightweight migrations:

        - If legacy `LegacySetting` table exists and `ConfigEntry` is empty,
          migrate rows into `ConfigEntry`.
        - Add missing columns via `ALTER TABLE` when possible.
        """
        # 1) Ensure SQLModel created base metadata
        SQLModel.metadata.create_all(self._engine)

        # 2) Detect legacy table presence via sqlite_master
        with self._engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"), {"t": "legacysetting"})
            legacy_table_exists = res.first() is not None
            # Note: table name for LegacySetting may be 'legacysetting' or 'setting'
            if not legacy_table_exists:
                res2 = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND (name='setting' OR name='legacysetting')"))
                legacy_table_exists = res2.first() is not None

        # 3) If legacy table exists and no config entries, migrate
        with Session(self._engine) as sess:
            has_entries = sess.exec(select(ConfigEntry).limit(1)).first() is not None
            if legacy_table_exists and not has_entries:
                # read from whichever old table exists
                with self._engine.connect() as conn:
                    try:
                        rows = conn.execute(text("SELECT key, value FROM setting")).fetchall()
                    except Exception:
                        try:
                            rows = conn.execute(text("SELECT key, value FROM legacysetting")).fetchall()
                        except Exception:
                            rows = []
                for k, v in rows:
                    entry = ConfigEntry(key=k, value=str(v), value_type="str", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
                    sess.add(entry)
                sess.commit()

        # 4) Add missing columns (SQLite supports ADD COLUMN)
        # We'll attempt to add columns present in ConfigEntry but not in the table.
        # Get current pragma table_info
        with self._engine.connect() as conn:
            try:
                info = conn.execute(text("PRAGMA table_info('configentry')")).fetchall()
                existing_cols = {row[1] for row in info}
            except Exception:
                existing_cols = set()

            # Desired extra columns
            desired = {
                "value_type": "TEXT",
                "description": "TEXT",
                "is_immutable": "INTEGER",
                "created_at": "TEXT",
                "updated_at": "TEXT",
            }
            for col, sqltype in desired.items():
                if col not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE configentry ADD COLUMN {col} {sqltype}"))
                    except Exception:
                        # best-effort: ignore failures
                        pass


def migrate_env_to_db(env_path: str | Path | None = None, db_path: str | Path | None = None) -> None:
    """Migrate an existing .env file into the DB-backed store.

    If `env_path` is None the default .env adjacent to the project root is used.
    If `db_path` is None the default DB path is used.
    """
    env = Path(env_path) if env_path is not None else PROJECT_ROOT.parent / ".env"
    if not env.exists():
        return
    es = EnvStore(env)
    values = es.read_all()
    ds = DBStore(db_path)
    ds.write_many(values)


def get_store() -> object:
    """Return the configured store.

    DB-backed store is the default. To opt-out and use the legacy `.env`
    file store set `SETTINGS_USE_DB=0` in the environment.
    """
    use_db_env = os.getenv("SETTINGS_USE_DB")
    if use_db_env is not None:
        use_db = use_db_env in ("1", "true", "True")
    else:
        use_db = True

    if use_db:
        db_path = os.getenv("SETTINGS_DB_PATH")
        return DBStore(db_path)
    return EnvStore()
