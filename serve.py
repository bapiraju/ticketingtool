"""
Application server entry point.

This module starts the Uvicorn server with centralized logging configuration.
"""

import uvicorn
from pathlib import Path
from app.core import setup_logging, settings
from loguru import logger


if __name__ == "__main__":
    # If running with reload enabled, write logs outside the project
    # directory so the reloader doesn't see log file writes as code changes.
    if settings.reload:
        alt_logs_dir = Path.cwd().parent / "ticketingtool_dev_logs"
        alt_logs_dir.mkdir(parents=True, exist_ok=True)
        # Point the settings to the alternate log file location before setup
        try:
            settings.log_file_path = str((alt_logs_dir / "application.log").resolve())
        except Exception:
            # safest-effort: ignore if settings attribute cannot be set
            pass

    # Initialize centralized logging (this must happen first!)
    setup_logging()
    try:
        logger.info(
            f"Starting Uvicorn server on {settings.host}:{settings.port} with reload={settings.reload}"
        )

        # log_config=None disables Uvicorn's default logging
        # This allows our InterceptHandler to capture all Uvicorn logs
        # Build absolute paths for exclude patterns so WatchFiles ignores them
        cwd = Path.cwd()
        logs_dir = str((cwd / "logs").resolve())
        venv_dir = str((cwd / ".venv").resolve())

        uvicorn.run(
            "app.main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            # Prevent the reloader from watching our log files and venv
            reload_excludes=[logs_dir, venv_dir],
            log_config=None,  # Disable default logging
            log_level=None,   # Let our logging system handle it
        )
    except KeyboardInterrupt:
        logger.info("Shutdown signal received, exiting gracefully")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")