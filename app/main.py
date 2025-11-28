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


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Ticketing Tool",
        description="A ticketing tool for personal use",
        version="0.1.0",
    )
    
    # Include all API routes
    app.include_router(api_router)
    
    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Application startup")
    
    # Add shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Application shutdown")
    
    return app


# Create the application instance
app = create_app()