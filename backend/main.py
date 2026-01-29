"""
AlphaGenome Dashboard - FastAPI Application

Main entry point for the backend API server.
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add parent directory to path so 'backend' can be imported as a package
backend_dir = Path(__file__).parent
if str(backend_dir.parent) not in sys.path:
    sys.path.insert(0, str(backend_dir.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings, ensure_directories
from backend.db import init_db
from backend.api import (
    files_router,
    variants_router,
    analysis_router,
    annotations_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AlphaGenome Dashboard API...")
    ensure_directories()
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down AlphaGenome Dashboard API...")


# Create FastAPI application
app = FastAPI(
    title="AlphaGenome Dashboard API",
    description="""
    Personal genome analysis dashboard powered by Google DeepMind's AlphaGenome.
    
    ## Features
    
    - **VCF Parsing**: Load and parse VCF files from whole genome sequencing
    - **Variant Analysis**: Deep variant effect prediction using AlphaGenome
    - **Gene Expression**: Predict impact on gene expression across tissues
    - **Splicing Analysis**: Identify splice site alterations
    - **ClinVar Integration**: Cross-reference with known pathogenic variants
    - **Pharmacogenomics**: Drug-gene interaction analysis via PharmGKB
    
    ## Getting Started
    
    1. Place your VCF files in `data/vcf/`
    2. Use `/api/files` to discover and load VCF files
    3. Browse variants with `/api/variants`
    4. Run AlphaGenome analysis with `/api/analysis`
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files_router, prefix="/api")
app.include_router(variants_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(annotations_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AlphaGenome Dashboard API",
        "version": "1.0.0",
        "documentation": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/status")
async def api_status():
    """Get overall API status and configuration."""
    from backend.config import get_settings

    settings = get_settings()

    return {
        "status": "running",
        "vcf_data_dir": str(settings.vcf_data_dir),
        "annotations_dir": str(settings.annotations_dir),
        "alphagenome_configured": bool(settings.alphagenome_api_key),
        "endpoints": {
            "files": "/api/files",
            "variants": "/api/variants",
            "analysis": "/api/analysis",
            "annotations": "/api/annotations",
        },
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
