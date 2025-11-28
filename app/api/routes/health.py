"""
Health check endpoints for application monitoring.
"""

from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
def health_check():
    """Check if the application is running."""
    logger.info("Health check requested")
    return {"status": "healthy"}


@router.get("/live")
def liveness_probe():
    """Kubernetes liveness probe endpoint."""
    logger.debug("Liveness probe requested")
    return {"status": "alive"}


@router.get("/ready")
def readiness_probe():
    """Kubernetes readiness probe endpoint."""
    logger.debug("Readiness probe requested")
    return {"status": "ready"}
