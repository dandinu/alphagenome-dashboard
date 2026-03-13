"""
AlphaGenome Dashboard - Analysis API Routes

Endpoints for AlphaGenome variant analysis including liftover,
7 specialized scorers, epigenomics, ISM, and plot generation.
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import (
    Variant,
    AnalysisResult,
    AnalysisRequest,
    ISMRequest,
    BatchAnalysisRequest,
    AnalysisResultResponse,
    VariantAnalysisResponse,
    BatchJobResponse,
    VariantResponse,
)
from backend.services import get_alphagenome_client, VariantInput, get_plot_path
from backend.services.plot_generator import (
    generate_track_overlay,
    generate_contact_map,
    generate_sashimi_plot,
    generate_ism_seqlogo,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])

# In-memory job tracking (use Redis in production)
_batch_jobs = {}


# ------------------------------------------------------------------ #
# DRY helper
# ------------------------------------------------------------------ #


def _build_variant_input(variant: Variant) -> VariantInput:
    """Build a VariantInput from a DB Variant, adding chr prefix if needed."""
    chrom = variant.chromosome
    if not chrom.startswith("chr"):
        chrom = f"chr{chrom}"
    return VariantInput(
        chromosome=chrom,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
    )


def _get_variant_or_404(variant_id: int, db: Session) -> Variant:
    """Fetch a variant from the DB or raise 404."""
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return variant


# ------------------------------------------------------------------ #
# Existing endpoints
# ------------------------------------------------------------------ #


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

    Uses all 7 specialized scorers with GRCh37->GRCh38 liftover applied.
    """
    variant = _get_variant_or_404(request.variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        results = client.score_variant(
            variant=variant_input,
            analysis_types=request.analysis_types,
            gene_symbol=variant.gene_symbol,
        )

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

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    """Queue batch variant scoring."""
    variants = db.query(Variant).filter(Variant.id.in_(request.variant_ids)).all()

    if len(variants) != len(request.variant_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Some variants not found. Found {len(variants)} of {len(request.variant_ids)}",
        )

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
    variant = _get_variant_or_404(variant_id, db)

    analyses = (
        db.query(AnalysisResult).filter(AnalysisResult.variant_id == variant_id).all()
    )

    expression_impact = None
    splicing_impact = None
    chromatin_impact = None
    histone_impact = None
    tf_binding_impact = None
    contact_map_impact = None
    composite_splicing_score = None
    plots = {}

    for analysis in analyses:
        if analysis.analysis_type == "RNA_SEQ":
            expression_impact = analysis.score_details
        elif analysis.analysis_type in ("SPLICE_SITES", "SPLICE_JUNCTIONS"):
            splicing_impact = analysis.score_details
            if analysis.score_details and "composite_splicing_score" in analysis.score_details:
                composite_splicing_score = analysis.score_details["composite_splicing_score"]
        elif analysis.analysis_type in ("ATAC", "DNASE"):
            chromatin_impact = analysis.score_details
        elif analysis.analysis_type == "CHIP_HISTONE":
            histone_impact = analysis.score_details
        elif analysis.analysis_type == "CHIP_TF":
            tf_binding_impact = analysis.score_details
        elif analysis.analysis_type == "CONTACT_MAPS":
            contact_map_impact = analysis.score_details

        # Check for saved plots
        plot_path = get_plot_path(variant_id, analysis.analysis_type)
        if plot_path:
            plots[analysis.analysis_type] = f"/api/analysis/{variant_id}/plot/{analysis.analysis_type}"

    return VariantAnalysisResponse(
        variant=VariantResponse.model_validate(variant),
        analyses=[AnalysisResultResponse.model_validate(a) for a in analyses],
        expression_impact=expression_impact,
        splicing_impact=splicing_impact,
        chromatin_impact=chromatin_impact,
        histone_impact=histone_impact,
        tf_binding_impact=tf_binding_impact,
        contact_map_impact=contact_map_impact,
        composite_splicing_score=composite_splicing_score,
        plots=plots if plots else None,
    )


# ------------------------------------------------------------------ #
# Expression & Splicing (existing, updated to use helpers)
# ------------------------------------------------------------------ #


@router.post("/expression/{variant_id}")
async def analyze_expression(
    variant_id: int, tissues: Optional[List[str]] = None, db: Session = Depends(get_db)
):
    """Analyze gene expression impact of a variant."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        return client.analyze_expression_impact(variant=variant_input, tissues=tissues)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing expression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/splicing/{variant_id}")
async def analyze_splicing(variant_id: int, db: Session = Depends(get_db)):
    """Analyze splicing impact of a variant (includes composite splicing score)."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        return client.analyze_splicing_impact(variant=variant_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing splicing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# New endpoints: Epigenomics
# ------------------------------------------------------------------ #


@router.post("/histone/{variant_id}")
async def analyze_histone(
    variant_id: int, tissues: Optional[List[str]] = None, db: Session = Depends(get_db)
):
    """Analyze histone modification impact of a variant."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        return client.analyze_histone_impact(variant=variant_input, tissues=tissues)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing histone impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tf-binding/{variant_id}")
async def analyze_tf_binding(
    variant_id: int, tissues: Optional[List[str]] = None, db: Session = Depends(get_db)
):
    """Analyze transcription factor binding impact of a variant."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        return client.analyze_tf_binding(variant=variant_input, tissues=tissues)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing TF binding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contacts/{variant_id}")
async def analyze_contacts(
    variant_id: int, tissues: Optional[List[str]] = None, db: Session = Depends(get_db)
):
    """Analyze 3D chromatin contact changes from a variant."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        return client.analyze_3d_contacts(variant=variant_input, tissues=tissues)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing 3D contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# ISM endpoint
# ------------------------------------------------------------------ #


@router.post("/ism/{variant_id}")
async def analyze_ism(
    variant_id: int,
    request: ISMRequest = ISMRequest(),
    db: Session = Depends(get_db),
):
    """Run in silico mutagenesis around a variant."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        result = client.run_ism(
            variant=variant_input,
            output_types=request.output_types,
            window_size=request.window_size,
        )

        # Save ISM result to DB
        analysis = AnalysisResult(
            variant_id=variant.id,
            analysis_type="ISM",
            score=None,
            score_details=result,
            plot_data={},
            model_version="alphagenome-v1",
            analyzed_at=datetime.utcnow(),
        )
        db.add(analysis)
        db.commit()

        # Generate ISM plot if matrix data is available
        if "matrix" in result and "error" not in result["matrix"]:
            plot_path = generate_ism_seqlogo(result["matrix"], variant.id)
            if plot_path:
                result["plot_url"] = f"/api/analysis/{variant.id}/plot/ISM"

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error running ISM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# Full analysis endpoint
# ------------------------------------------------------------------ #


@router.post("/full/{variant_id}")
async def run_full_analysis(
    variant_id: int,
    tissues: Optional[List[str]] = None,
    db: Session = Depends(get_db),
):
    """Run ALL analyses on a variant at once."""
    variant = _get_variant_or_404(variant_id, db)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        full_results = client.run_full_analysis(
            variant=variant_input,
            tissues=tissues,
            gene_symbol=variant.gene_symbol,
        )

        # Save scoring results to DB
        saved_analyses = []
        if full_results.get("scoring"):
            for result in full_results["scoring"]:
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
                saved_analyses.append(result.analysis_type)
            db.commit()

        # Generate plots where applicable
        plots = {}
        try:
            predictions = client.predict_variant(
                variant=variant_input,
                analysis_types=["RNA_SEQ", "CONTACT_MAPS"],
            )
            ref = predictions["reference"]
            alt = predictions["alternate"]

            rna_plot = generate_track_overlay(ref, alt, "RNA_SEQ", variant.id)
            if rna_plot:
                plots["RNA_SEQ"] = f"/api/analysis/{variant.id}/plot/RNA_SEQ"

            contact_plot = generate_contact_map(ref, alt, variant.id, diff=True)
            if contact_plot:
                plots["CONTACT_MAPS_diff"] = f"/api/analysis/{variant.id}/plot/CONTACT_MAPS_diff"

            sashimi_plot = generate_sashimi_plot(ref, alt, variant.id)
            if sashimi_plot:
                plots["SASHIMI"] = f"/api/analysis/{variant.id}/plot/SASHIMI"
        except Exception as e:
            logger.warning(f"Plot generation failed during full analysis: {e}")

        return {
            "variant_id": variant.id,
            "analyses_saved": saved_analyses,
            "expression": full_results.get("expression"),
            "splicing": full_results.get("splicing"),
            "histone": full_results.get("histone"),
            "tf_binding": full_results.get("tf_binding"),
            "contacts": full_results.get("contacts"),
            "plots": plots,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error running full analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# Plot serving endpoint
# ------------------------------------------------------------------ #


@router.get("/{variant_id}/plot/{analysis_type}")
async def get_plot(variant_id: int, analysis_type: str):
    """Serve a generated plot image for a variant analysis."""
    plot_path = get_plot_path(variant_id, analysis_type)
    if not plot_path:
        raise HTTPException(status_code=404, detail="Plot not found")

    return FileResponse(
        path=str(plot_path),
        media_type="image/png",
        filename=f"{analysis_type}.png",
    )


# ------------------------------------------------------------------ #
# Background task
# ------------------------------------------------------------------ #


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

            variant_input = _build_variant_input(variant)

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
