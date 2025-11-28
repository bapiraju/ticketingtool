"""
Item-related endpoints (example routes).
"""

from typing import Union
from fastapi import APIRouter
from loguru import logger

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def list_items():
    """Get list of all items."""
    logger.info("GET /items - Listing all items")
    return {"items": []}


@router.get("/{item_id}")
def get_item(item_id: int, q: Union[str, None] = None):
    """Get a specific item by ID."""
    logger.info(f"GET /items/{item_id} - query parameter: {q}")
    return {"item_id": item_id, "q": q}


@router.post("/")
def create_item(name: str):
    """Create a new item."""
    logger.info(f"POST /items - Creating item: {name}")
    return {"name": name, "created": True}
