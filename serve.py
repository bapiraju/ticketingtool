"""
Application server entry point.

This module starts the Uvicorn server with centralized logging configuration.
"""

import uvicorn
from app.core import setup_logging, AppConfig
from loguru import logger


if __name__ == "__main__":
    # Initialize centralized logging (this must happen first!)
    setup_logging()
    
    try:
        logger.info(
            f"Starting Uvicorn server on {AppConfig.HOST}:{AppConfig.PORT} "
            f"with reload={AppConfig.RELOAD}"
        )
        # log_config=None disables Uvicorn's default logging
        # This allows our InterceptHandler to capture all Uvicorn logs
        uvicorn.run(
            "app.main:app",
            host=AppConfig.HOST,
            port=AppConfig.PORT,
            reload=AppConfig.RELOAD,
            log_config=None,  # Disable default logging
            log_level=None,   # Let our logging system handle it
        )
    except KeyboardInterrupt:
        logger.info("Shutdown signal received, exiting gracefully")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")