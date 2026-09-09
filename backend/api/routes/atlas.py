"""
AlphaGenome Dashboard - Atlas API Routes

Endpoints for precomputed AlphaGenome Atlas scores: batch AVI annotation
of parsed VCFs, per-variant lookup, top-impact panel, and attribution-driven
triage of the live deep-dive analyses.
"""

import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import get_db
from backend.models import (
    Variant,
    VCFFile,
    AnalysisResult,
    AtlasAnnotation,
    AtlasAnnotationResponse,
    AtlasAnnotateRequest,
    AtlasJobResponse,
    TopVariantEntry,
    TriageResponse,
    VariantResponse,
    AnalysisResultResponse,
)
from backend.services import get_atlas_client, get_alphagenome_client
from backend.services.atlas_client import AtlasResult
from backend.services import genome_utils
from backend.api.routes.analysis import _build_variant_input, _get_variant_or_404

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/atlas", tags=["atlas"])

# In-memory job tracking (matches the analysis batch-job pattern)
_atlas_jobs = {}

# Modality attribution buckets -> live analysis types for triage
TRIAGE_MAP = {
    "expression": ["RNA_SEQ"],
    "splicing": ["SPLICE_SITES", "SPLICE_JUNCTIONS"],
    "chromatin": ["ATAC", "DNASE"],
    "tf_binding": ["CHIP_TF"],
    "histone": ["CHIP_HISTONE"],
}
ALL_TRIAGE_TYPES = [
    "RNA_SEQ",
    "SPLICE_SITES",
    "SPLICE_JUNCTIONS",
    "ATAC",
    "DNASE",
    "CHIP_TF",
    "CHIP_HISTONE",
    "CONTACT_MAPS",
]


def _save_annotation(
    db: Session, variant_id: int, result: AtlasResult
) -> AtlasAnnotation:
    """Insert or update the AtlasAnnotation row for a variant."""
    annotation = (
        db.query(AtlasAnnotation)
        .filter(AtlasAnnotation.variant_id == variant_id)
        .first()
    )
    if annotation is None:
        annotation = AtlasAnnotation(variant_id=variant_id)
        db.add(annotation)
    annotation.avi_score = result.avi_score
    annotation.feature_importance = result.feature_importance
    annotation.modality_scores = result.modality_scores
    annotation.attributions = result.attributions
    annotation.top_modality = result.top_modality
    annotation.atlas_version = result.atlas_version
    annotation.lifted_chromosome = result.lifted_chromosome
    annotation.lifted_position = result.lifted_position
    annotation.annotated_at = datetime.utcnow()
    return annotation


def _build_annotate_query(db: Session, request: AtlasAnnotateRequest):
    """Query for SNV variants matching the annotation filters."""
    query = db.query(Variant).filter(
        Variant.vcf_file_id == request.vcf_file_id,
        Variant.variant_type == "SNP",
    )
    if request.non_ref_only:
        query = query.filter(Variant.genotype != "0/0")
    if request.pass_only:
        query = query.filter(Variant.filter_status.in_(["PASS", ".", None]))
    if request.min_quality is not None:
        query = query.filter(Variant.quality >= request.min_quality)
    if request.coding_only:
        query = query.filter(Variant.is_coding.is_(True))
    if request.chromosomes:
        query = query.filter(Variant.chromosome.in_(request.chromosomes))
    return query


@router.post("/annotate", response_model=AtlasJobResponse)
async def annotate_vcf(
    request: AtlasAnnotateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Batch-annotate a VCF file's SNVs with precomputed Atlas AVI scores."""
    vcf_file = db.query(VCFFile).filter(VCFFile.id == request.vcf_file_id).first()
    if not vcf_file:
        raise HTTPException(status_code=404, detail="VCF file not found")

    for job in _atlas_jobs.values():
        if (
            job["vcf_file_id"] == request.vcf_file_id
            and job["status"] in ("queued", "running")
        ):
            raise HTTPException(
                status_code=409,
                detail="An Atlas annotation job is already running for this file",
            )

    total_in_file = (
        db.query(Variant).filter(Variant.vcf_file_id == request.vcf_file_id).count()
    )
    candidate_ids = [row[0] for row in _build_annotate_query(db, request).with_entities(Variant.id).all()]
    skipped_non_snv = (
        db.query(Variant)
        .filter(
            Variant.vcf_file_id == request.vcf_file_id,
            Variant.variant_type != "SNP",
        )
        .count()
    )

    skipped_existing = 0
    if not request.overwrite and candidate_ids:
        existing = {
            row[0]
            for row in db.query(AtlasAnnotation.variant_id)
            .filter(AtlasAnnotation.variant_id.in_(candidate_ids))
            .all()
        }
        skipped_existing = len(existing)
        candidate_ids = [vid for vid in candidate_ids if vid not in existing]

    job_id = str(uuid.uuid4())
    _atlas_jobs[job_id] = {
        "status": "queued",
        "vcf_file_id": request.vcf_file_id,
        "total_variants": len(candidate_ids),
        "completed": 0,
        "failed": 0,
        "skipped_non_snv": skipped_non_snv,
        "skipped_existing": skipped_existing,
        "created_at": datetime.utcnow(),
    }
    logger.info(
        f"Atlas job {job_id}: {len(candidate_ids)} SNVs to annotate "
        f"({total_in_file} total in file, {skipped_non_snv} non-SNV, "
        f"{skipped_existing} already annotated)"
    )

    background_tasks.add_task(_atlas_annotate_task, job_id, candidate_ids)
    return _job_response(job_id)


def _job_response(job_id: str) -> AtlasJobResponse:
    job = _atlas_jobs[job_id]
    return AtlasJobResponse(
        job_id=job_id,
        status=job["status"],
        total_variants=job["total_variants"],
        completed=job["completed"],
        failed=job["failed"],
        skipped_non_snv=job["skipped_non_snv"],
        skipped_existing=job["skipped_existing"],
        created_at=job["created_at"],
    )


@router.get("/job/{job_id}", response_model=AtlasJobResponse)
async def get_atlas_job_status(job_id: str):
    """Get status of an Atlas annotation job."""
    if job_id not in _atlas_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_response(job_id)


@router.get("/top", response_model=List[TopVariantEntry])
async def get_top_variants(
    vcf_file_id: Optional[int] = None,
    limit: int = Query(default=10, ge=1, le=100),
    non_ref_only: bool = True,
    db: Session = Depends(get_db),
):
    """Top variants by AVI score for the dashboard panel."""
    query = (
        db.query(Variant, AtlasAnnotation)
        .join(AtlasAnnotation, AtlasAnnotation.variant_id == Variant.id)
        .filter(AtlasAnnotation.avi_score.isnot(None))
    )
    if vcf_file_id is not None:
        query = query.filter(Variant.vcf_file_id == vcf_file_id)
    if non_ref_only:
        query = query.filter(Variant.genotype != "0/0")
    rows = query.order_by(AtlasAnnotation.avi_score.desc()).limit(limit).all()

    return [
        TopVariantEntry(
            variant=VariantResponse.model_validate(variant),
            avi_score=annotation.avi_score,
            top_modality=annotation.top_modality,
            attributions=annotation.attributions,
        )
        for variant, annotation in rows
    ]


@router.get("/variant/{variant_id}", response_model=AtlasAnnotationResponse)
async def get_variant_annotation(variant_id: int, db: Session = Depends(get_db)):
    """Get (or fetch on demand) the Atlas annotation for a single variant."""
    variant = _get_variant_or_404(variant_id, db)

    annotation = (
        db.query(AtlasAnnotation)
        .filter(AtlasAnnotation.variant_id == variant_id)
        .first()
    )
    if annotation:
        return AtlasAnnotationResponse.model_validate(annotation)

    if not genome_utils.is_snv(variant.reference, variant.alternate):
        raise HTTPException(
            status_code=422,
            detail=(
                "Atlas covers SNVs only — use POST /api/analysis/full/"
                f"{variant_id} (live API) for this variant"
            ),
        )

    try:
        result = get_atlas_client().lookup_variant(_build_variant_input(variant))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    annotation = _save_annotation(db, variant_id, result)
    db.commit()
    db.refresh(annotation)
    return AtlasAnnotationResponse.model_validate(annotation)


def _compute_triage(annotation: Optional[AtlasAnnotation]) -> TriageResponse:
    """Map attribution shares to recommended live analysis types."""
    if annotation is None or not annotation.attributions:
        return TriageResponse(
            source="fallback_full",
            recommended_analysis_types=ALL_TRIAGE_TYPES,
            skipped=[],
        )

    threshold = get_settings().atlas_triage_threshold
    attributions = annotation.attributions
    recommended = []
    for modality, types in TRIAGE_MAP.items():
        if attributions.get(modality, 0.0) >= threshold:
            recommended.extend(types)
    # 3D contacts only when chromatin signal is strong
    if attributions.get("chromatin", 0.0) >= 2 * threshold:
        recommended.append("CONTACT_MAPS")

    # If nothing clears the threshold, fall back to the top modality
    if not recommended:
        recommended = list(TRIAGE_MAP.get(annotation.top_modality, ALL_TRIAGE_TYPES))

    skipped = [t for t in ALL_TRIAGE_TYPES if t not in recommended]
    return TriageResponse(
        source="atlas",
        avi_score=annotation.avi_score,
        attributions=attributions,
        recommended_analysis_types=recommended,
        skipped=skipped,
    )


@router.get("/triage/{variant_id}", response_model=TriageResponse)
async def get_triage(variant_id: int, db: Session = Depends(get_db)):
    """Recommend which deep-dive analyses to run based on Atlas attributions."""
    _get_variant_or_404(variant_id, db)
    annotation = (
        db.query(AtlasAnnotation)
        .filter(AtlasAnnotation.variant_id == variant_id)
        .first()
    )
    return _compute_triage(annotation)


@router.post("/triage/{variant_id}/run")
async def run_triaged_analysis(variant_id: int, db: Session = Depends(get_db)):
    """Run only the Atlas-recommended deep-dive analyses on a variant."""
    variant = _get_variant_or_404(variant_id, db)
    annotation = (
        db.query(AtlasAnnotation)
        .filter(AtlasAnnotation.variant_id == variant_id)
        .first()
    )
    triage = _compute_triage(annotation)
    variant_input = _build_variant_input(variant)

    try:
        client = get_alphagenome_client()
        results = client.score_variant(
            variant=variant_input,
            analysis_types=triage.recommended_analysis_types,
            gene_symbol=variant.gene_symbol,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error running triaged analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    saved = []
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
        saved.append(AnalysisResultResponse.model_validate(analysis))

    return {"triage": triage, "analyses": saved}


# ------------------------------------------------------------------ #
# Background task
# ------------------------------------------------------------------ #


def _atlas_annotate_task(job_id: str, variant_ids: List[int]):
    """Background task: annotate variants with Atlas scores in chunks."""
    from backend.db import SessionLocal

    db = SessionLocal()
    client = get_atlas_client()
    settings = get_settings()
    chunk_size = settings.atlas_batch_size

    _atlas_jobs[job_id]["status"] = "running"
    try:
        for start in range(0, len(variant_ids), chunk_size):
            chunk_ids = variant_ids[start : start + chunk_size]
            variants = db.query(Variant).filter(Variant.id.in_(chunk_ids)).all()
            variants_by_id = {v.id: v for v in variants}
            ordered = [variants_by_id[vid] for vid in chunk_ids if vid in variants_by_id]

            inputs = [_build_variant_input(v) for v in ordered]
            results = client.lookup_batch(inputs)

            for variant, result in zip(ordered, results):
                if isinstance(result, Exception):
                    logger.warning(
                        f"Atlas lookup failed for variant {variant.id}: {result}"
                    )
                    _atlas_jobs[job_id]["failed"] += 1
                else:
                    _save_annotation(db, variant.id, result)
                    _atlas_jobs[job_id]["completed"] += 1
            db.commit()
        _atlas_jobs[job_id]["status"] = "completed"
    except Exception as e:
        logger.error(f"Atlas annotation job {job_id} failed: {e}")
        _atlas_jobs[job_id]["status"] = "failed"
    finally:
        db.close()
