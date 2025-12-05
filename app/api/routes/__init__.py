"""
API routes module - centralized router imports.

This module imports all route modules and provides a single
access point for registering routes with the FastAPI app.
"""

from fastapi import APIRouter
from app.api.routes import health, items, admin

# Create a combined router for all API routes
api_router = APIRouter()

# Include all route modules
api_router.include_router(health.router)
api_router.include_router(items.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
