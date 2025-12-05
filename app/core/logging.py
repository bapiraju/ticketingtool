"""
Centralized logging setup using Loguru with standard library interception.

This module:
1. Sets up Loguru for all application logging
2. Intercepts standard library logging from FastAPI, Uvicorn, AsyncIO, etc.
3. Routes all logs through a unified system
4. Configures file rotation, compression, and retention from environment variables
"""

import logging
import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

# Remove default handler
logger.remove()

# Ensure logs directory exists
log_dir = Path(settings.log_file_path).parent
log_dir.mkdir(parents=True, exist_ok=True)


class InterceptHandler(logging.Handler):
    """
    Intercepts standard logging calls and routes them to Loguru.
    
    This ensures all logs from any library using standard logging
    (FastAPI, Uvicorn, AsyncIO, Starlette, etc.) go through our
    centralized logging system with consistent formatting.
    
    How it works:
    1. Captures all logging.Handler emit() calls
    2. Converts logging.LogRecord to Loguru level
    3. Routes through Loguru for consistent formatting
    4. Maintains proper stack depth for accurate line numbers
    """
    
    def emit(self, record):
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller to get correct stack depth
        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _configure_library_loggers() -> None:
    """Configure and propagate logs from third-party libraries to root logger."""
    libraries = [
        "uvicorn", "uvicorn.access", "uvicorn.error",
        "fastapi", "asyncio", "starlette", "starlette.middleware.base", "starlette.requests",
    ]
    for logger_name in libraries:
        lib_logger = logging.getLogger(logger_name)
        lib_logger.handlers = []  # Remove any existing handlers
        lib_logger.propagate = True  # Ensure logs propagate to root
        lib_logger.setLevel(logging.DEBUG)  # Capture all levels


def setup_logging(level: str = None) -> None:
    """
    Configure centralized logging for the entire application.
    
    This function:
    1. Sets up Loguru with console and file output
    2. Configures file rotation and compression
    3. Intercepts standard logging from all libraries
    4. Routes library logs (uvicorn, fastapi, etc.) through Loguru
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses LOG_LEVEL from .env file.
    
    Example:
        from app.core.logging import setup_logging
        setup_logging()  # Uses .env LOG_LEVEL
        setup_logging(level="DEBUG")  # Override with DEBUG
    """
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    try:
        logger.remove()
    except Exception:
        pass

    # Use provided level or get from config
    if level is None:
        level = settings.log_level.value if hasattr(settings.log_level, "value") else str(settings.log_level)
    else:
        # normalize
        level = str(level).upper()
    
    # Add console output with nice formatting
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True,
    )
    
    # Add file output with rotation
    # Only add file logging in non-reload mode. When Uvicorn runs with
    # the auto-reloader it writes files which can trigger the reloader
    # itself. To avoid reload loops during development, skip file logging
    # while `settings.reload` is True.
    try:
        if not getattr(settings, "reload", False):
            logger.add(
                settings.log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=settings.log_file_rotation,
                compression=settings.log_file_compression,
                retention=settings.log_file_retention,
                level=level,
                backtrace=True,
                diagnose=True,
            )
        else:
            logger.debug("Reload mode enabled — skipping file logging to avoid reloader loops")
    except Exception:
        # If settings isn't available or an error occurs, fall back to adding file
        # logging to avoid losing logs in production scenarios.
        logger.add(
            settings.log_file_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=settings.log_file_rotation,
            compression=settings.log_file_compression,
            retention=settings.log_file_retention,
            level=level,
            backtrace=True,
            diagnose=True,
        )
    
    # Intercept standard library logging
    # This captures logs from uvicorn, fastapi, asyncio, starlette, etc.
    logging.basicConfig(
        handlers=[InterceptHandler()],
        level=logging.DEBUG,  # Capture all levels at root
    )
    
    _configure_library_loggers()
    
    logger.info(f"Logging system initialized with level: {level}")
    logger.debug(f"Log file: {settings.log_file_path}")
    logger.debug(f"File rotation: {settings.log_file_rotation}")
