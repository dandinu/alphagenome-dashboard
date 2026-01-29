"""
AlphaGenome Dashboard - Analysis API Routes

Endpoints for AlphaGenome variant analysis.
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import (
    Variant,
    AnalysisResult,
    AnalysisRequest,
    BatchAnalysisRequest,
    AnalysisResultResponse,
    VariantAnalysisResponse,
    BatchJobResponse,
    VariantResponse,
)
from backend.services import get_alphagenome_client, VariantInput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory job tracking (use Redis in production)
_batch_jobs = {}


@router.get("/output-types")
async def get_output_types():
    """Get available AlphaGenome output types."""
    client = get_alphagenome_client()
    return {
        "output_types": client.get_available_outputs(),
        "tissues": client.get_tissue_ontology(),
    }


@router.post("/score", response_model=List[AnalysisResultResponse])
async def score_variant(request: AnalysisRequest, db: Session = Depends(get_db)):
    """
    Score a single variant using AlphaGenome.

    This performs deep variant effect prediction using AlphaGenome's
    neural network model.
    """
    # Get variant from database
    variant = db.query(Variant).filter(Variant.id == request.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    # Create input for AlphaGenome
    variant_input = VariantInput(
        chromosome=f"chr{variant.chromosome}"
        if not variant.chromosome.startswith("chr")
        else variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
    )

    try:
        client = get_alphagenome_client()
        results = client.score_variant(
            variant=variant_input,
            analysis_types=request.analysis_types,
            gene_symbol=variant.gene_symbol,
        )

        # Save results to database
        saved_results = []
        for result in results:
            analysis = AnalysisResult(
                variant_id=variant.id,
                analysis_type=result.analysis_type,
                score=result.score,
                score_details=result.score_details,
                plot_data=result.plot_data,
                model_version=result.model_version,
                analyzed_at=result.analyzed_at,
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            saved_results.append(AnalysisResultResponse.model_validate(analysis))

        return saved_results

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error scoring variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=BatchJobResponse)
async def batch_score_variants(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Queue batch variant scoring.

    This starts a background job to score multiple variants.
    Use GET /analysis/job/{job_id} to check status.
    """
    # Verify all variants exist
    variants = db.query(Variant).filter(Variant.id.in_(request.variant_ids)).all()

    if len(variants) != len(request.variant_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Some variants not found. Found {len(variants)} of {len(request.variant_ids)}",
        )

    # Create job
    job_id = str(uuid.uuid4())
    _batch_jobs[job_id] = {
        "status": "queued",
        "total_variants": len(request.variant_ids),
        "completed": 0,
        "failed": 0,
        "created_at": datetime.utcnow(),
        "variant_ids": request.variant_ids,
        "analysis_types": request.analysis_types,
    }

    # Start background task
    background_tasks.add_task(
        _batch_score_task, job_id, request.variant_ids, request.analysis_types
    )

    return BatchJobResponse(
        job_id=job_id,
        status="queued",
        total_variants=len(request.variant_ids),
        completed=0,
        failed=0,
        created_at=datetime.utcnow(),
    )


@router.get("/job/{job_id}", response_model=BatchJobResponse)
async def get_job_status(job_id: str):
    """Get status of a batch analysis job."""
    if job_id not in _batch_jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _batch_jobs[job_id]
    return BatchJobResponse(
        job_id=job_id,
        status=job["status"],
        total_variants=job["total_variants"],
        completed=job["completed"],
        failed=job["failed"],
        created_at=job["created_at"],
    )


@router.get("/{variant_id}", response_model=VariantAnalysisResponse)
async def get_variant_analysis(variant_id: int, db: Session = Depends(get_db)):
    """Get all analysis results for a variant."""
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    analyses = (
        db.query(AnalysisResult).filter(AnalysisResult.variant_id == variant_id).all()
    )

    # Process results by type
    expression_impact = None
    splicing_impact = None
    chromatin_impact = None

    for analysis in analyses:
        if analysis.analysis_type == "RNA_SEQ":
            expression_impact = analysis.score_details
        elif analysis.analysis_type in ["SPLICE_SITES", "SPLICE_JUNCTIONS"]:
            splicing_impact = analysis.score_details
        elif analysis.analysis_type in ["ATAC", "DNASE"]:
            chromatin_impact = analysis.score_details

    return VariantAnalysisResponse(
        variant=VariantResponse.model_validate(variant),
        analyses=[AnalysisResultResponse.model_validate(a) for a in analyses],
        expression_impact=expression_impact,
        splicing_impact=splicing_impact,
        chromatin_impact=chromatin_impact,
    )


@router.post("/expression/{variant_id}")
async def analyze_expression(
    variant_id: int, tissues: Optional[List[str]] = None, db: Session = Depends(get_db)
):
    """
    Analyze gene expression impact of a variant.

    Optionally filter by specific tissues.
    """
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    variant_input = VariantInput(
        chromosome=f"chr{variant.chromosome}"
        if not variant.chromosome.startswith("chr")
        else variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
    )

    try:
        client = get_alphagenome_client()
        result = client.analyze_expression_impact(
            variant=variant_input,
            tissues=tissues,
        )

        return result

    except Exception as e:
        logger.error(f"Error analyzing expression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/splicing/{variant_id}")
async def analyze_splicing(variant_id: int, db: Session = Depends(get_db)):
    """Analyze splicing impact of a variant."""
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    variant_input = VariantInput(
        chromosome=f"chr{variant.chromosome}"
        if not variant.chromosome.startswith("chr")
        else variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
    )

    try:
        client = get_alphagenome_client()
        result = client.analyze_splicing_impact(variant=variant_input)

        return result

    except Exception as e:
        logger.error(f"Error analyzing splicing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _batch_score_task(job_id: str, variant_ids: List[int], analysis_types: List[str]):
    """Background task for batch scoring."""
    from backend.db import SessionLocal

    db = SessionLocal()
    client = get_alphagenome_client()

    _batch_jobs[job_id]["status"] = "running"

    for vid in variant_ids:
        try:
            variant = db.query(Variant).filter(Variant.id == vid).first()
            if not variant:
                _batch_jobs[job_id]["failed"] += 1
                continue

            variant_input = VariantInput(
                chromosome=f"chr{variant.chromosome}"
                if not variant.chromosome.startswith("chr")
                else variant.chromosome,
                position=variant.position,
                reference=variant.reference,
                alternate=variant.alternate,
            )

            results = client.score_variant(
                variant=variant_input,
                analysis_types=analysis_types,
                gene_symbol=variant.gene_symbol,
            )

            for result in results:
                analysis = AnalysisResult(
                    variant_id=vid,
                    analysis_type=result.analysis_type,
                    score=result.score,
                    score_details=result.score_details,
                    plot_data=result.plot_data,
                    model_version=result.model_version,
                    analyzed_at=result.analyzed_at,
                )
                db.add(analysis)

            db.commit()
            _batch_jobs[job_id]["completed"] += 1

        except Exception as e:
            logger.error(f"Error scoring variant {vid}: {e}")
            _batch_jobs[job_id]["failed"] += 1

    _batch_jobs[job_id]["status"] = "completed"
    db.close()
