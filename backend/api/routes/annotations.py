"""
AlphaGenome Dashboard - Annotations API Routes

Endpoints for ClinVar and PharmGKB annotations.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import (
    Variant,
    ClinVarAnnotation,
    PharmGKBAnnotation,
    ClinVarAnnotationResponse,
    PharmGKBAnnotationResponse,
    PharmacogenomicsPanel,
    PharmaGeneReport,
    DiseaseRiskPanel,
    DiseaseRiskVariant,
    VariantResponse,
)
from backend.services import get_clinvar_service, get_pharmgkb_service, PHARMACOGENES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/annotations", tags=["annotations"])


# ============== ClinVar Endpoints ==============


@router.get("/clinvar/status")
async def clinvar_status(db: Session = Depends(get_db)):
    """Get ClinVar database status."""
    service = get_clinvar_service(db)
    return {
        "loaded": service.is_loaded(),
        "total_annotations": service.get_annotation_count(),
    }


@router.post("/clinvar/load")
async def load_clinvar(
    background_tasks: BackgroundTasks,
    assembly: Optional[str] = Query(None, description="Genome assembly (GRCh37 or GRCh38). Defaults to config setting."),
    db: Session = Depends(get_db),
):
    """
    Load ClinVar variant_summary.txt.gz into the database.

    This runs as a background task since loading can take several minutes.
    The file should be downloaded first using: python scripts/download_clinvar.py
    """
    service = get_clinvar_service(db)

    # Check if already loaded
    if service.is_loaded():
        return {
            "status": "already_loaded",
            "message": "ClinVar data is already loaded",
            "total_annotations": service.get_annotation_count(),
        }

    # Start background task
    background_tasks.add_task(_load_clinvar_task, assembly)

    return {
        "status": "loading",
        "message": "ClinVar data loading started in background. Check /clinvar/status for progress.",
    }


def _load_clinvar_task(assembly: str):
    """Background task to load ClinVar data."""
    from backend.db import SessionLocal

    db = SessionLocal()
    try:
        service = get_clinvar_service(db)
        count = service.load_variant_summary(assembly=assembly)
        logger.info(f"ClinVar loading complete: {count} records")
    except Exception as e:
        logger.error(f"Error loading ClinVar: {e}")
    finally:
        db.close()


@router.get("/clinvar/rsid/{rsid}", response_model=List[ClinVarAnnotationResponse])
async def lookup_clinvar_by_rsid(rsid: str, db: Session = Depends(get_db)):
    """Look up ClinVar annotation by rsID."""
    service = get_clinvar_service(db)
    annotations = service.lookup_by_rsid(rsid)
    return [ClinVarAnnotationResponse.model_validate(a) for a in annotations]


@router.get(
    "/clinvar/gene/{gene_symbol}", response_model=List[ClinVarAnnotationResponse]
)
async def lookup_clinvar_by_gene(gene_symbol: str, db: Session = Depends(get_db)):
    """Look up ClinVar annotations for a gene."""
    service = get_clinvar_service(db)
    annotations = service.lookup_by_gene(gene_symbol)
    return [ClinVarAnnotationResponse.model_validate(a) for a in annotations]


@router.get("/clinvar/pathogenic")
async def get_pathogenic_variants(
    gene_symbol: Optional[str] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """Get pathogenic variants from ClinVar."""
    service = get_clinvar_service(db)
    annotations = service.get_pathogenic_variants(gene_symbol, limit)
    return [ClinVarAnnotationResponse.model_validate(a) for a in annotations]


# ============== PharmGKB Endpoints ==============


@router.get("/pharmgkb/status")
async def pharmgkb_status(db: Session = Depends(get_db)):
    """Get PharmGKB database status."""
    service = get_pharmgkb_service(db)
    return {
        "loaded": service.is_loaded(),
        "total_annotations": service.get_annotation_count(),
        "pharmacogenes": list(PHARMACOGENES.keys()),
    }


@router.get("/pharmgkb/rsid/{rsid}", response_model=List[PharmGKBAnnotationResponse])
async def lookup_pharmgkb_by_rsid(rsid: str, db: Session = Depends(get_db)):
    """Look up PharmGKB annotations by rsID."""
    service = get_pharmgkb_service(db)
    annotations = service.lookup_by_rsid(rsid)
    return [PharmGKBAnnotationResponse.model_validate(a) for a in annotations]


@router.get(
    "/pharmgkb/gene/{gene_symbol}", response_model=List[PharmGKBAnnotationResponse]
)
async def lookup_pharmgkb_by_gene(gene_symbol: str, db: Session = Depends(get_db)):
    """Look up PharmGKB annotations for a gene."""
    service = get_pharmgkb_service(db)
    annotations = service.lookup_by_gene(gene_symbol)
    return [PharmGKBAnnotationResponse.model_validate(a) for a in annotations]


@router.get("/pharmgkb/drug/{drug_name}")
async def lookup_by_drug(drug_name: str, db: Session = Depends(get_db)):
    """Look up variants associated with a drug."""
    service = get_pharmgkb_service(db)
    annotations = service.lookup_by_drug(drug_name)
    return [PharmGKBAnnotationResponse.model_validate(a) for a in annotations]


@router.get("/pharmgkb/genes")
async def get_pharmacogenes():
    """Get list of pharmacogenes with details."""
    return PHARMACOGENES


# ============== Panel Endpoints ==============


@router.get("/panels/pharmacogenomics", response_model=PharmacogenomicsPanel)
async def get_pharmacogenomics_panel(
    vcf_file_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """
    Generate pharmacogenomics panel report.

    Analyzes user's variants against known pharmacogenes and
    provides drug response recommendations.
    """
    pharmgkb_service = get_pharmgkb_service(db)

    # Get user's variants in pharmacogenes
    query = db.query(Variant).filter(
        Variant.gene_symbol.in_(list(PHARMACOGENES.keys()))
    )
    if vcf_file_id:
        query = query.filter(Variant.vcf_file_id == vcf_file_id)

    variants = query.all()

    # Group variants by gene
    variants_by_gene = {}
    for v in variants:
        gene = v.gene_symbol.upper()
        if gene not in variants_by_gene:
            variants_by_gene[gene] = []
        variants_by_gene[gene].append(v)

    # Generate reports for each pharmacogene
    gene_reports = []
    total_actionable = 0

    for gene_symbol, gene_info in PHARMACOGENES.items():
        user_variants = variants_by_gene.get(gene_symbol, [])

        # Get drug associations
        drug_associations = pharmgkb_service.get_gene_drug_associations(gene_symbol)

        # Check for actionable variants
        rsids = [v.rsid for v in user_variants if v.rsid]
        actionable = pharmgkb_service.get_actionable_variants(rsids) if rsids else []

        if user_variants or drug_associations:
            recommendations = []
            for ann in actionable:
                recommendations.append(
                    f"{ann.drug_name}: {ann.phenotype_category} "
                    f"(Evidence: {ann.level_of_evidence})"
                )
                total_actionable += 1

            gene_reports.append(
                PharmaGeneReport(
                    gene_symbol=gene_symbol,
                    gene_name=gene_info["name"],
                    variants=[VariantResponse.model_validate(v) for v in user_variants],
                    drugs=drug_associations,
                    recommendations=recommendations,
                )
            )

    return PharmacogenomicsPanel(
        genes=gene_reports,
        total_actionable_variants=total_actionable,
        summary=f"Found {len(variants)} variants in {len(variants_by_gene)} pharmacogenes. "
        f"{total_actionable} variants have actionable clinical annotations.",
    )


@router.get("/panels/disease-risk", response_model=DiseaseRiskPanel)
async def get_disease_risk_panel(
    vcf_file_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """
    Generate disease risk panel report.

    Identifies pathogenic and likely pathogenic variants
    from ClinVar annotations.
    """
    clinvar_service = get_clinvar_service(db)

    # Get user's variants with rsIDs
    query = db.query(Variant).filter(Variant.rsid.isnot(None))
    if vcf_file_id:
        query = query.filter(Variant.vcf_file_id == vcf_file_id)

    variants = query.all()
    rsid_to_variant = {v.rsid: v for v in variants}

    pathogenic = []
    likely_pathogenic = []
    risk_factors = []

    for rsid, variant in rsid_to_variant.items():
        clinvar_entries = clinvar_service.lookup_by_rsid(rsid)

        for entry in clinvar_entries:
            sig = entry.clinical_significance or ""

            disease_variant = DiseaseRiskVariant(
                variant=VariantResponse.model_validate(variant),
                disease_name=entry.disease_names or "Unknown",
                disease_id=entry.disease_ids,
                clinical_significance=sig,
                inheritance=None,
                risk_category="unknown",
            )

            if "Pathogenic" in sig and "Likely" not in sig:
                disease_variant.risk_category = "high"
                pathogenic.append(disease_variant)
            elif "Likely_pathogenic" in sig:
                disease_variant.risk_category = "moderate"
                likely_pathogenic.append(disease_variant)
            elif "risk_factor" in sig.lower():
                disease_variant.risk_category = "low"
                risk_factors.append(disease_variant)

    return DiseaseRiskPanel(
        pathogenic_variants=pathogenic,
        likely_pathogenic_variants=likely_pathogenic,
        risk_factors=risk_factors,
        total_high_risk=len(pathogenic),
        total_moderate_risk=len(likely_pathogenic),
        summary=f"Found {len(pathogenic)} pathogenic variants, "
        f"{len(likely_pathogenic)} likely pathogenic variants, "
        f"and {len(risk_factors)} risk factors.",
    )
