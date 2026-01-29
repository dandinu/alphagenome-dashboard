"""API routes module."""

from backend.api.routes.files import router as files_router
from backend.api.routes.variants import router as variants_router
from backend.api.routes.analysis import router as analysis_router
from backend.api.routes.annotations import router as annotations_router

__all__ = [
    "files_router",
    "variants_router",
    "analysis_router",
    "annotations_router",
]
