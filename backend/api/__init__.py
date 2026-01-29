"""API module."""

from backend.api.routes import (
    files_router,
    variants_router,
    analysis_router,
    annotations_router,
)

__all__ = [
    "files_router",
    "variants_router",
    "analysis_router",
    "annotations_router",
]
