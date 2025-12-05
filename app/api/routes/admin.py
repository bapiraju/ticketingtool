from typing import Optional, Dict, Any
import os
import sys
from fastapi import APIRouter, Body, Query, HTTPException, status, Depends
from pydantic import BaseModel
from loguru import logger

from app.core.config import (
    settings,
    update_and_reload,
    write_settings_to_env,
    _read_env_file,
    ENV_FILE,
    validate_setting_value,
)
from app.core.logging import setup_logging
from app.core.security import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminSettingsUpdate(BaseModel):
    LOG_LEVEL: Optional[str]
    LOG_FILE_PATH: Optional[str]
    LOG_FILE_ROTATION: Optional[str]
    LOG_FILE_RETENTION: Optional[str]
    LOG_FILE_COMPRESSION: Optional[str]
    HOST: Optional[str]
    PORT: Optional[int]
    RELOAD: Optional[bool]


def _allowed_keys() -> Dict[str, Any]:
    """Return a mapping of allowed env keys to their current values."""
    # Merge settings known fields with raw store values so that runtime-created
    # keys (those not defined on Settings) are also visible via the admin API.
    env_values = _read_env_file(ENV_FILE)
    model_values = settings.model_dump(by_alias=True)
    merged = {**env_values, **model_values}
    return merged


def _validate_and_update_settings(updates: Dict[str, Any]) -> Dict[str, str]:
    """Validate and prepare settings updates."""
    validated_updates: Dict[str, str] = {}
    errors: Dict[str, str] = {}
    for k, v in updates.items():
        try:
            validated = validate_setting_value(k, v)
            validated_updates[k] = str(validated)
        except Exception as e:
            errors[k] = str(e)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"validation_errors": errors})
    return validated_updates


def _persist_and_reload_settings(updates: Dict[str, str], restart: bool = False) -> None:
    """Persist settings, reload config, reconfigure logging, and optionally restart."""
    try:
        write_settings_to_env(updates)
        update_and_reload(updates)
    except Exception as e:
        logger.exception("Failed to write and reload settings")
        raise HTTPException(status_code=500, detail=str(e))

    try:
        setup_logging()
    except Exception:
        logger.exception("Failed to reconfigure logging after settings update")

    if restart:
        logger.info("Restarting process to apply settings")
        try:
            logger.complete()
        except Exception:
            pass
        python = sys.executable
        os.execv(python, [python] + sys.argv)


@router.get("/settings")
def get_settings(_user=Depends(require_role("user"))):
    """Return current settings (all)."""
    return _allowed_keys()


@router.get("/settings/{key}")
def get_setting(key: str, _user=Depends(require_role("user"))):
    """Return a single configuration value by env key (alias)."""
    allowed = _allowed_keys()
    if key not in allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
    return {key: allowed[key]}


class SingleValue(BaseModel):
    value: Any


@router.put("/settings/{key}")
def put_setting(key: str, payload: SingleValue = Body(...), restart: bool = Query(False), _admin=Depends(require_role("admin"))):
    """Add a new configuration key to the .env file and reload settings.

    This endpoint only allows *adding* new keys. To update existing keys use POST /admin/settings/{key}.
    Optional `restart=true` will execv the process to restart.
    """
    env_values = _read_env_file(ENV_FILE)
    if key in env_values:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Setting '{key}' already exists. Use POST to update existing keys.",
        )

    # immutable keys cannot be created/changed
    if key in (settings.immutable_keys or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Setting '{key}' is immutable")

    updates = _validate_and_update_settings({key: payload.value})
    _persist_and_reload_settings(updates, restart=restart)
    return {"ok": True, "added": updates}


@router.post("/settings/{key}")
def post_setting(key: str, payload: SingleValue = Body(...), restart: bool = Query(False), _admin=Depends(require_role("admin"))):
    """Update an existing configuration key in the .env file and reload settings.

    This endpoint only allows updating keys that already exist in the .env file. To add new keys use PUT /admin/settings/{key}.
    """
    env_values = _read_env_file(ENV_FILE)
    if key not in env_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Setting '{key}' is not present in the .env file; cannot update non-existing key",
        )

    # immutable keys cannot be changed
    if key in (settings.immutable_keys or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Setting '{key}' is immutable")

    updates = _validate_and_update_settings({key: payload.value})
    _persist_and_reload_settings(updates, restart=restart)
    return {"ok": True, "updated": updates}


@router.put("/settings")
def put_settings_bulk(payload: Dict[str, Any] = Body(...), restart: bool = Query(False), _admin=Depends(require_role("admin"))):
    """Create multiple new settings in .env. If any key already exists, the operation is rejected.

    Body should be a mapping of KEY -> value.
    """
    env_values = _read_env_file(ENV_FILE)
    conflicts = [k for k in payload.keys() if k in env_values]
    if conflicts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"conflicts": conflicts})

    # Check immutables
    immutables = set(settings.immutable_keys or [])
    blocked = [k for k in payload.keys() if k in immutables]
    if blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"immutable": blocked})

    updates = _validate_and_update_settings(payload)
    _persist_and_reload_settings(updates, restart=restart)
    return {"ok": True, "added": updates}


@router.post("/settings")
def post_settings_bulk(payload: Dict[str, Any] = Body(...), restart: bool = Query(False), _admin=Depends(require_role("admin"))):
    """Update multiple existing settings in .env. If any key does not exist, the operation is rejected.

    Body should be a mapping of KEY -> value.
    """
    env_values = _read_env_file(ENV_FILE)
    missing = [k for k in payload.keys() if k not in env_values]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"missing": missing})

    immutables = set(settings.immutable_keys or [])
    blocked = [k for k in payload.keys() if k in immutables]
    if blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"immutable": blocked})

    updates = _validate_and_update_settings(payload)
    _persist_and_reload_settings(updates, restart=restart)
    return {"ok": True, "updated": updates}
