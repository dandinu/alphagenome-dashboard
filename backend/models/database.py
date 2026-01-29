"""
AlphaGenome Dashboard - Database Models
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from backend.db.database import Base


class VCFFile(Base):
    """Tracks loaded VCF files."""

    __tablename__ = "vcf_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True)
    filepath = Column(String(512))
    sample_name = Column(String(255))
    total_variants = Column(Integer, default=0)
    coding_variants = Column(Integer, default=0)
    annotated_variants = Column(
        Integer, default=0
    )  # Variants with VEP/SnpEff annotations
    loaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    variants = relationship(
        "Variant", back_populates="vcf_file", cascade="all, delete-orphan"
    )


class Variant(Base):
    """Stores parsed variants from VCF files."""

    __tablename__ = "variants"

    id = Column(Integer, primary_key=True, index=True)
    vcf_file_id = Column(Integer, ForeignKey("vcf_files.id"), index=True)

    # Core variant info
    chromosome = Column(String(10), index=True)
    position = Column(Integer, index=True)
    rsid = Column(String(50), index=True)
    reference = Column(String(500))
    alternate = Column(String(500))
    quality = Column(Float)
    filter_status = Column(String(50))

    # Genotype info
    genotype = Column(String(10))  # e.g., "0/1", "1/1"
    zygosity = Column(String(20))  # "heterozygous", "homozygous"

    # Variant classification
    variant_type = Column(String(20))  # "SNP", "INS", "DEL", "MNP"
    is_coding = Column(Boolean, default=False, index=True)
    is_annotated = Column(
        Boolean, default=False, index=True
    )  # Has VEP/SnpEff annotations

    # Gene annotations (from VCF INFO or external)
    gene_symbol = Column(String(50), index=True)
    gene_id = Column(String(50))
    transcript_id = Column(String(50))
    consequence = Column(String(100))  # e.g., "missense_variant"
    impact = Column(String(20))  # "HIGH", "MODERATE", "LOW", "MODIFIER"

    # Amino acid change
    protein_change = Column(String(50))  # e.g., "p.Arg123Cys"
    codon_change = Column(String(50))

    # Population frequencies
    af_gnomad = Column(Float)
    af_1000g = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    vcf_file = relationship("VCFFile", back_populates="variants")
    analysis_results = relationship(
        "AnalysisResult", back_populates="variant", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_variant_location", "chromosome", "position"),
        Index("idx_variant_gene", "gene_symbol", "is_coding"),
    )


class AnalysisResult(Base):
    """Stores AlphaGenome analysis results for variants."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("variants.id"), index=True)

    # Analysis type
    analysis_type = Column(String(50), index=True)  # "RNA_SEQ", "SPLICE", "ATAC", etc.

    # Scores
    score = Column(Float)
    score_details = Column(JSON)  # Detailed per-track scores

    # Visualization data
    plot_data = Column(JSON)  # Data for frontend visualization

    # Metadata
    model_version = Column(String(50))
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    variant = relationship("Variant", back_populates="analysis_results")


class ClinVarAnnotation(Base):
    """ClinVar annotations for variants."""

    __tablename__ = "clinvar_annotations"

    id = Column(Integer, primary_key=True, index=True)

    # Variant identifier (for joining)
    chromosome = Column(String(10), index=True)
    position = Column(Integer, index=True)
    reference = Column(String(500))
    alternate = Column(String(500))

    # ClinVar specific
    clinvar_id = Column(String(50), index=True)
    rsid = Column(String(50), index=True)

    # Clinical significance
    clinical_significance = Column(String(100))  # "Pathogenic", "Benign", etc.
    review_status = Column(String(100))

    # Disease associations
    disease_names = Column(Text)  # Semicolon-separated
    disease_ids = Column(Text)  # MedGen, OMIM IDs

    # Gene
    gene_symbol = Column(String(50), index=True)

    # Timestamps
    last_updated = Column(DateTime)

    __table_args__ = (Index("idx_clinvar_location", "chromosome", "position"),)


class PharmGKBAnnotation(Base):
    """PharmGKB pharmacogenomics annotations."""

    __tablename__ = "pharmgkb_annotations"

    id = Column(Integer, primary_key=True, index=True)

    # Variant identifier
    rsid = Column(String(50), index=True)
    gene_symbol = Column(String(50), index=True)

    # Drug associations
    drug_name = Column(String(255))
    drug_id = Column(String(50))

    # Clinical annotation
    phenotype_category = Column(String(100))  # "Toxicity", "Efficacy", "Dosage", etc.
    significance = Column(String(50))  # Level of evidence

    # Guideline info
    guideline_id = Column(String(50))
    guideline_name = Column(String(255))

    # Allele info
    allele = Column(String(100))
    annotation_text = Column(Text)

    # Metadata
    level_of_evidence = Column(String(10))  # "1A", "1B", "2A", "2B", "3", "4"

    __table_args__ = (Index("idx_pharmgkb_gene_drug", "gene_symbol", "drug_name"),)
