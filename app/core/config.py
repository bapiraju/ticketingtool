"""
Configuration management using environment variables.
Load settings from .env file for easy configuration.
"""

import os
from enum import Enum
from pathlib import Path
from typing import Optional, Dict
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings
from app.core.store import get_store

# Path to project root and .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class LogLevel(str, Enum):
    """
    Valid logging levels as an enumeration.
    
    Advantages:
    1. Type safety - prevents invalid values at runtime
    2. IDE autocomplete - see available levels while coding
    3. Single source of truth - define levels once, use everywhere
    4. Easy iteration - can loop over all valid levels
    5. Better documentation - explicit enum values are self-documenting
    6. Prevents typos - invalid strings cause AttributeError instead of silent bugs
    """
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    # Logging settings
    log_level: LogLevel = Field(default=LogLevel.INFO, alias="LOG_LEVEL")
    log_file_path: str = Field(default="logs/application.log", alias="LOG_FILE_PATH")
    log_file_rotation: str = Field(default="500 MB", alias="LOG_FILE_ROTATION")
    log_file_retention: str = Field(default="7 days", alias="LOG_FILE_RETENTION")
    log_file_compression: str = Field(default="zip", alias="LOG_FILE_COMPRESSION")

    # Application settings
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=True, alias="RELOAD")
    app_name: str = Field(default="Ticketing Tool", alias="APP_NAME")
    app_description: str = Field(default="A ticketing tool for personal use", alias="APP_DESCRIPTION")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    # Security settings for JWT
    admin_jwt_secret: str = Field(default="admin-secret-change-me", alias="ADMIN_JWT_SECRET")
    user_jwt_secret: str = Field(default="user-secret-change-me", alias="USER_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # Immutable keys that cannot be changed via admin endpoints
    immutable_keys: list[str] = Field(default_factory=lambda: ["PATH"], alias="IMMUTABLE_KEYS")

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = True
        populate_by_name = True


def _initialize_settings() -> Settings:
    """Initialize settings with fallback to defaults on validation failure."""
    try:
        return Settings()
    except Exception as e:
        import warnings
        warnings.warn(f"Settings validation failed during import: {e}. Falling back to defaults.")
        try:
            return Settings.model_construct()
        except Exception:
            return Settings()


# Module-level singleton settings instance
settings = _initialize_settings()


def _read_env_file(path: Path) -> Dict[str, str]:
    # Delegate to configured store (env file or DB)
    store = get_store()
    return store.read_all()


def _write_env_file(path: Path, values: Dict[str, str]) -> None:
    # Write via store abstraction
    store = get_store()
    store.write_many(values)


def write_settings_to_env(updates: Dict[str, str]) -> None:
    """Update the .env file with provided key/value pairs.

    Keys should be environment variable names (e.g., LOG_LEVEL).
    """
    store = get_store()
    # store.write_many will merge/update existing keys
    store.write_many({k: str(v) for k, v in updates.items()})


def reload_settings() -> None:
    """Reload the module-level settings from the .env file."""
    global settings
    # If using a DB-backed store, populate os.environ first so pydantic can read values
    store = get_store()
    try:
        values = store.read_all()
        for k, v in values.items():
            os.environ[k] = str(v)
    except Exception:
        # fallback: ignore
        pass
    
    new_settings = _initialize_settings()

    # Preserve the identity of the module-level `settings` object so callers
    # holding a reference (e.g., tests) see updates. If the current `settings`
    # is an instance of Settings, update its attributes in-place; otherwise,
    # replace the module-level reference.
    if isinstance(settings, Settings):
        new_values = new_settings.model_dump()
        for attr_name, val in new_values.items():
            try:
                setattr(settings, attr_name, val)
            except Exception:
                # ignore attributes that can't be set
                pass
    else:
        settings = new_settings


def update_and_reload(updates: Dict[str, str]) -> None:
    """Write updates to .env, then reload settings in memory."""
    write_settings_to_env(updates)
    reload_settings()


def validate_setting_value(key: str, value: object) -> object:
    """Validate a single setting key/value pair against the Settings model.

    Attempts to validate using the provided alias first (e.g. 'LOG_LEVEL'),
    then falls back to the snake_case field name (e.g. 'log_level'). Returns
    the validated value (possibly coerced to the appropriate type) or raises
    a ValueError on validation failure.
    """
    # Map alias -> field name in Settings
    fields = Settings.model_fields
    target_field = None
    target_info = None
    for fname, finfo in fields.items():
        alias = getattr(finfo, "alias", None) or fname
        if alias == key:
            target_field = fname
            target_info = finfo
            break

    # If not found by alias, try snake-case field name
    if target_field is None:
        snake = key.lower()
        if snake in fields:
            target_field = snake
            target_info = fields[snake]

    if target_field is None:
        # Unknown key: no validation available, return raw value
        return value

    # Create a tiny pydantic model to validate the single field type
    try:
        from pydantic import create_model

        annotation = getattr(target_info, "annotation", None) or getattr(target_info, "outer_type_", None) or object
        Tmp = create_model("_SingleField", value=(annotation, ...))
        validated = Tmp.model_validate({"value": value})
        return validated.value
    except Exception as e:
        raise ValueError(f"Invalid value for setting '{key}': {e}") from e


__all__ = ["settings", "Settings", "LogLevel", "reload_settings", "update_and_reload", "write_settings_to_env"]
