"""
AlphaGenome Dashboard - Variants API Routes

Endpoints for querying and filtering variants.
"""

import logging
from typing import Optional, List
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from backend.db import get_db
from backend.models import (
    Variant,
    VCFFile,
    AnalysisResult,
    ClinVarAnnotation,
    PharmGKBAnnotation,
    VariantResponse,
    VariantListResponse,
    VariantStats,
    VariantFilter,
    ClinVarAnnotationResponse,
    PharmGKBAnnotationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/variants", tags=["variants"])


@router.get("", response_model=VariantListResponse)
async def list_variants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    chromosome: Optional[str] = None,
    gene_symbol: Optional[str] = None,
    rsid: Optional[str] = None,
    is_coding: Optional[bool] = None,
    impact: Optional[str] = None,
    consequence: Optional[str] = None,
    zygosity: Optional[str] = None,
    min_quality: Optional[float] = None,
    has_clinvar: Optional[bool] = None,
    search: Optional[str] = None,
    vcf_file_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    List variants with filtering and pagination.
    """
    query = db.query(Variant)

    # Apply filters
    if vcf_file_id:
        query = query.filter(Variant.vcf_file_id == vcf_file_id)

    if chromosome:
        chrom = chromosome.replace("chr", "")
        query = query.filter(Variant.chromosome == chrom)

    if gene_symbol:
        query = query.filter(Variant.gene_symbol.ilike(f"%{gene_symbol}%"))

    if rsid:
        if not rsid.startswith("rs"):
            rsid = f"rs{rsid}"
        query = query.filter(Variant.rsid == rsid)

    if is_coding is not None:
        query = query.filter(Variant.is_coding == is_coding)

    if impact:
        impacts = impact.split(",")
        query = query.filter(Variant.impact.in_(impacts))

    if consequence:
        query = query.filter(Variant.consequence.ilike(f"%{consequence}%"))

    if zygosity:
        query = query.filter(Variant.zygosity == zygosity)

    if min_quality:
        query = query.filter(Variant.quality >= min_quality)

    if search:
        query = query.filter(
            or_(
                Variant.rsid.ilike(f"%{search}%"),
                Variant.gene_symbol.ilike(f"%{search}%"),
                Variant.protein_change.ilike(f"%{search}%"),
            )
        )

    # Get total count
    total = query.count()
    total_pages = ceil(total / page_size)

    # Apply pagination
    offset = (page - 1) * page_size
    variants = (
        query.order_by(Variant.chromosome, Variant.position)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Enrich with annotations
    variant_responses = []
    for v in variants:
        response = VariantResponse.model_validate(v)

        # Check for ClinVar annotation (rsID first, then position-based fallback)
        clinvar = None
        if v.rsid:
            clinvar = (
                db.query(ClinVarAnnotation)
                .filter(ClinVarAnnotation.rsid == v.rsid)
                .first()
            )
        if not clinvar:
            chrom = v.chromosome.replace("chr", "")
            clinvar = (
                db.query(ClinVarAnnotation)
                .filter(
                    ClinVarAnnotation.chromosome == chrom,
                    ClinVarAnnotation.position == v.position,
                    ClinVarAnnotation.reference == v.reference,
                    ClinVarAnnotation.alternate == v.alternate,
                )
                .first()
            )
        if clinvar:
            response.clinvar = ClinVarAnnotationResponse.model_validate(clinvar)

        # Check for PharmGKB annotations (rsID only — PharmGKB has no position data)
        if v.rsid:
            pharmgkb = (
                db.query(PharmGKBAnnotation)
                .filter(PharmGKBAnnotation.rsid == v.rsid)
                .all()
            )
            if pharmgkb:
                response.pharmgkb = [
                    PharmGKBAnnotationResponse.model_validate(p) for p in pharmgkb
                ]

        # Check for analysis results
        has_analysis = (
            db.query(AnalysisResult).filter(AnalysisResult.variant_id == v.id).first()
            is not None
        )
        response.has_analysis = has_analysis

        variant_responses.append(response)

    return VariantListResponse(
        variants=variant_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=VariantStats)
async def get_variant_stats(
    vcf_file_id: Optional[int] = None, db: Session = Depends(get_db)
):
    """Get summary statistics for variants."""
    query = db.query(Variant)
    if vcf_file_id:
        query = query.filter(Variant.vcf_file_id == vcf_file_id)

    total = query.count()
    coding = query.filter(Variant.is_coding == True).count()
    annotated = query.filter(Variant.is_annotated == True).count()
    snps = query.filter(Variant.variant_type == "SNP").count()
    indels = query.filter(Variant.variant_type.in_(["INS", "DEL"])).count()

    # By chromosome
    chrom_counts = (
        db.query(Variant.chromosome, func.count(Variant.id))
        .group_by(Variant.chromosome)
        .all()
    )
    by_chromosome = {c: n for c, n in chrom_counts}

    # By impact
    impact_counts = (
        db.query(Variant.impact, func.count(Variant.id))
        .filter(Variant.impact.isnot(None))
        .group_by(Variant.impact)
        .all()
    )
    by_impact = {i: n for i, n in impact_counts if i}

    # By consequence (top 10)
    consequence_counts = (
        db.query(Variant.consequence, func.count(Variant.id))
        .filter(Variant.consequence.isnot(None))
        .group_by(Variant.consequence)
        .order_by(func.count(Variant.id).desc())
        .limit(10)
        .all()
    )
    by_consequence = {c: n for c, n in consequence_counts if c}

    # ClinVar stats via position-based join (works for unannotated VCFs without rsIDs)
    clinvar_join = (
        db.query(Variant.id, ClinVarAnnotation.clinical_significance)
        .join(
            ClinVarAnnotation,
            and_(
                ClinVarAnnotation.chromosome == Variant.chromosome,
                ClinVarAnnotation.position == Variant.position,
                ClinVarAnnotation.reference == Variant.reference,
                ClinVarAnnotation.alternate == Variant.alternate,
            ),
        )
    )
    if vcf_file_id:
        clinvar_join = clinvar_join.filter(Variant.vcf_file_id == vcf_file_id)

    clinvar_pathogenic = clinvar_join.filter(
        ClinVarAnnotation.clinical_significance.in_(
            [
                "Pathogenic", "Pathogenic/Likely pathogenic",
                "Pathogenic/Likely_pathogenic", "Likely pathogenic",
                "Likely_pathogenic",
            ]
        )
    ).count()

    clinvar_benign = clinvar_join.filter(
        ClinVarAnnotation.clinical_significance.in_(
            [
                "Benign", "Benign/Likely benign", "Benign/Likely_benign",
                "Likely benign", "Likely_benign",
            ]
        )
    ).count()

    clinvar_vus = clinvar_join.filter(
        ClinVarAnnotation.clinical_significance.in_(
            ["Uncertain significance", "Uncertain_significance"]
        )
    ).count()

    # PharmGKB stats (rsID-based only)
    rsids = [v.rsid for v in query.filter(Variant.rsid.isnot(None)).limit(10000).all()]
    pharmgkb_variants = (
        db.query(PharmGKBAnnotation)
        .filter(PharmGKBAnnotation.rsid.in_(rsids))
        .distinct(PharmGKBAnnotation.rsid)
        .count()
        if rsids
        else 0
    )

    return VariantStats(
        total_variants=total,
        coding_variants=coding,
        annotated_variants=annotated,
        snps=snps,
        indels=indels,
        by_chromosome=by_chromosome,
        by_impact=by_impact,
        by_consequence=by_consequence,
        clinvar_pathogenic=clinvar_pathogenic,
        clinvar_benign=clinvar_benign,
        clinvar_vus=clinvar_vus,
        pharmgkb_variants=pharmgkb_variants,
    )


@router.get("/{variant_id}", response_model=VariantResponse)
async def get_variant(variant_id: int, db: Session = Depends(get_db)):
    """Get a single variant by ID with full annotations."""
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")

    response = VariantResponse.model_validate(variant)

    # Add ClinVar annotation (rsID first, then position-based fallback)
    clinvar = None
    if variant.rsid:
        clinvar = (
            db.query(ClinVarAnnotation)
            .filter(ClinVarAnnotation.rsid == variant.rsid)
            .first()
        )
    if not clinvar:
        chrom = variant.chromosome.replace("chr", "")
        clinvar = (
            db.query(ClinVarAnnotation)
            .filter(
                ClinVarAnnotation.chromosome == chrom,
                ClinVarAnnotation.position == variant.position,
                ClinVarAnnotation.reference == variant.reference,
                ClinVarAnnotation.alternate == variant.alternate,
            )
            .first()
        )
    if clinvar:
        response.clinvar = ClinVarAnnotationResponse.model_validate(clinvar)

    # Add PharmGKB annotations
    if variant.rsid:
        pharmgkb = (
            db.query(PharmGKBAnnotation)
            .filter(PharmGKBAnnotation.rsid == variant.rsid)
            .all()
        )
        if pharmgkb:
            response.pharmgkb = [
                PharmGKBAnnotationResponse.model_validate(p) for p in pharmgkb
            ]

    # Check for analysis
    has_analysis = (
        db.query(AnalysisResult).filter(AnalysisResult.variant_id == variant.id).first()
        is not None
    )
    response.has_analysis = has_analysis

    return response


@router.get("/by-gene/{gene_symbol}")
async def get_variants_by_gene(
    gene_symbol: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get all variants for a gene."""
    query = db.query(Variant).filter(Variant.gene_symbol.ilike(gene_symbol))

    total = query.count()
    total_pages = ceil(total / page_size)
    offset = (page - 1) * page_size

    variants = query.order_by(Variant.position).offset(offset).limit(page_size).all()

    return {
        "gene_symbol": gene_symbol.upper(),
        "variants": [VariantResponse.model_validate(v) for v in variants],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/by-location/{chromosome}/{start}/{end}")
async def get_variants_by_location(
    chromosome: str, start: int, end: int, db: Session = Depends(get_db)
):
    """Get variants in a genomic region."""
    chrom = chromosome.replace("chr", "")

    variants = (
        db.query(Variant)
        .filter(
            Variant.chromosome == chrom,
            Variant.position >= start,
            Variant.position <= end,
        )
        .order_by(Variant.position)
        .all()
    )

    return {
        "region": f"{chromosome}:{start}-{end}",
        "variants": [VariantResponse.model_validate(v) for v in variants],
        "total": len(variants),
    }
