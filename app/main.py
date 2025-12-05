"""
Main FastAPI application factory.

This module creates and configures the FastAPI application with:
- Route registration
- Middleware setup
- Exception handling
- Application initialization
"""

from fastapi import FastAPI
from loguru import logger
from app.api import api_router
from app.core import settings
from app.core import store as store_mod
from app.core import config as config_mod


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
    )
    
    # Include all API routes
    app.include_router(api_router)
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup")
        try:
            store = store_mod.get_store()
            # If store is DB-backed and currently empty, migrate .env into the DB
            if hasattr(store, "is_empty") and store.is_empty():
                logger.info("Settings DB empty — migrating .env into DB if present")
                try:
                    store_mod.migrate_env_to_db()
                except Exception as e:
                    logger.warning(f"Migration from .env to DB failed: {e}")
            # Load settings from selected store into environment and pydantic settings
            try:
                config_mod.reload_settings()
                logger.info("Configuration loaded from store")
            except Exception as e:
                logger.warning(f"Failed to reload configuration from store: {e}")
        except Exception:
            # non-fatal: continue startup
            logger.exception("Failed to initialize settings store")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown")
    
    return app


# Create the application instance
app = create_app()