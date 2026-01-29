"""
AlphaGenome Dashboard - Pydantic Schemas
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============== VCF File Schemas ==============


class VCFFileBase(BaseModel):
    filename: str
    sample_name: Optional[str] = None


class VCFFileCreate(VCFFileBase):
    filepath: str


class VCFFileResponse(VCFFileBase):
    id: int
    filepath: str
    total_variants: int
    coding_variants: int
    annotated_variants: int = 0
    loaded_at: datetime

    class Config:
        from_attributes = True


class VCFFileList(BaseModel):
    files: List[VCFFileResponse]
    total: int


# ============== Variant Schemas ==============


class VariantBase(BaseModel):
    chromosome: str
    position: int
    reference: str
    alternate: str


class VariantCreate(VariantBase):
    vcf_file_id: int
    rsid: Optional[str] = None
    quality: Optional[float] = None
    filter_status: Optional[str] = None
    genotype: Optional[str] = None
    zygosity: Optional[str] = None
    variant_type: Optional[str] = None
    is_coding: bool = False
    is_annotated: bool = False
    gene_symbol: Optional[str] = None
    gene_id: Optional[str] = None
    transcript_id: Optional[str] = None
    consequence: Optional[str] = None
    impact: Optional[str] = None
    protein_change: Optional[str] = None
    codon_change: Optional[str] = None
    af_gnomad: Optional[float] = None
    af_1000g: Optional[float] = None


class VariantResponse(VariantBase):
    id: int
    vcf_file_id: int
    rsid: Optional[str]
    quality: Optional[float]
    filter_status: Optional[str]
    genotype: Optional[str]
    zygosity: Optional[str]
    variant_type: Optional[str]
    is_coding: bool
    is_annotated: bool = False
    gene_symbol: Optional[str]
    gene_id: Optional[str]
    transcript_id: Optional[str]
    consequence: Optional[str]
    impact: Optional[str]
    protein_change: Optional[str]
    codon_change: Optional[str]
    af_gnomad: Optional[float]
    af_1000g: Optional[float]
    created_at: datetime

    # Annotations (populated via joins)
    clinvar: Optional["ClinVarAnnotationResponse"] = None
    pharmgkb: Optional[List["PharmGKBAnnotationResponse"]] = None
    has_analysis: bool = False

    class Config:
        from_attributes = True


class VariantListResponse(BaseModel):
    variants: List[VariantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VariantFilter(BaseModel):
    """Filters for variant queries."""

    chromosome: Optional[str] = None
    gene_symbol: Optional[str] = None
    rsid: Optional[str] = None
    is_coding: Optional[bool] = None
    is_annotated: Optional[bool] = None
    impact: Optional[List[str]] = None  # ["HIGH", "MODERATE"]
    consequence: Optional[List[str]] = None
    has_clinvar: Optional[bool] = None
    clinical_significance: Optional[List[str]] = None
    min_quality: Optional[float] = None
    zygosity: Optional[str] = None


class VariantStats(BaseModel):
    """Summary statistics for variants."""

    total_variants: int
    coding_variants: int
    annotated_variants: int = 0
    snps: int
    indels: int
    by_chromosome: Dict[str, int]
    by_impact: Dict[str, int]
    by_consequence: Dict[str, int]
    clinvar_pathogenic: int
    clinvar_benign: int
    clinvar_vus: int
    pharmgkb_variants: int


# ============== Analysis Schemas ==============


class AnalysisRequest(BaseModel):
    """Request to analyze a variant with AlphaGenome."""

    variant_id: int
    analysis_types: List[str] = Field(
        default=["RNA_SEQ", "SPLICE_SITES", "ATAC"],
        description="Types of analysis to run",
    )
    ontology_terms: Optional[List[str]] = None


class BatchAnalysisRequest(BaseModel):
    """Request to analyze multiple variants."""

    variant_ids: List[int]
    analysis_types: List[str] = ["RNA_SEQ", "SPLICE_SITES"]
    priority: str = "normal"  # "high", "normal", "low"


class AnalysisResultResponse(BaseModel):
    id: int
    variant_id: int
    analysis_type: str
    score: Optional[float]
    score_details: Optional[Dict[str, Any]]
    plot_data: Optional[Dict[str, Any]]
    model_version: Optional[str]
    analyzed_at: datetime

    class Config:
        from_attributes = True


class VariantAnalysisResponse(BaseModel):
    """Full analysis response for a variant."""

    variant: VariantResponse
    analyses: List[AnalysisResultResponse]
    expression_impact: Optional[Dict[str, Any]] = None
    splicing_impact: Optional[Dict[str, Any]] = None
    chromatin_impact: Optional[Dict[str, Any]] = None


class BatchJobResponse(BaseModel):
    """Response for batch analysis job."""

    job_id: str
    status: str  # "queued", "running", "completed", "failed"
    total_variants: int
    completed: int
    failed: int
    created_at: datetime
    estimated_completion: Optional[datetime] = None


# ============== Annotation Schemas ==============


class ClinVarAnnotationResponse(BaseModel):
    id: int
    clinvar_id: Optional[str]
    rsid: Optional[str]
    clinical_significance: Optional[str]
    review_status: Optional[str]
    disease_names: Optional[str]
    disease_ids: Optional[str]
    gene_symbol: Optional[str]
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True


class PharmGKBAnnotationResponse(BaseModel):
    id: int
    rsid: Optional[str]
    gene_symbol: Optional[str]
    drug_name: Optional[str]
    drug_id: Optional[str]
    phenotype_category: Optional[str]
    significance: Optional[str]
    guideline_name: Optional[str]
    allele: Optional[str]
    annotation_text: Optional[str]
    level_of_evidence: Optional[str]

    class Config:
        from_attributes = True


# ============== Panel Schemas ==============


class PharmaGeneReport(BaseModel):
    """Pharmacogenomics report for a gene."""

    gene_symbol: str
    gene_name: str
    variants: List[VariantResponse]
    drugs: List[Dict[str, Any]]
    diplotype: Optional[str] = None
    phenotype: Optional[str] = None
    recommendations: List[str] = []


class PharmacogenomicsPanel(BaseModel):
    """Full pharmacogenomics panel response."""

    genes: List[PharmaGeneReport]
    total_actionable_variants: int
    summary: str


class DiseaseRiskVariant(BaseModel):
    """A variant with disease risk information."""

    variant: VariantResponse
    disease_name: str
    disease_id: Optional[str]
    clinical_significance: str
    inheritance: Optional[str]
    risk_category: str  # "high", "moderate", "low"


class DiseaseRiskPanel(BaseModel):
    """Disease risk panel response."""

    pathogenic_variants: List[DiseaseRiskVariant]
    likely_pathogenic_variants: List[DiseaseRiskVariant]
    risk_factors: List[DiseaseRiskVariant]
    total_high_risk: int
    total_moderate_risk: int
    summary: str


# Update forward references
VariantResponse.model_rebuild()
