"""
AlphaGenome Dashboard - ClinVar Annotation Service

Downloads and queries ClinVar variant annotations.
Supports both VCF and tab-delimited variant_summary.txt formats.
"""

import os
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.database import ClinVarAnnotation

logger = logging.getLogger(__name__)

# ClinVar clinical significance categories
CLINICAL_SIGNIFICANCE_CATEGORIES = {
    "pathogenic": [
        "Pathogenic",
        "Pathogenic/Likely pathogenic",
        "Pathogenic/Likely_pathogenic",
    ],
    "likely_pathogenic": ["Likely pathogenic", "Likely_pathogenic"],
    "vus": [
        "Uncertain significance",
        "Uncertain_significance",
        "Conflicting_interpretations_of_pathogenicity",
        "Conflicting interpretations of pathogenicity",
    ],
    "likely_benign": ["Likely benign", "Likely_benign"],
    "benign": ["Benign", "Benign/Likely benign", "Benign/Likely_benign"],
}

# Reverse mapping for category lookup
SIGNIFICANCE_TO_CATEGORY = {}
for category, values in CLINICAL_SIGNIFICANCE_CATEGORIES.items():
    for value in values:
        SIGNIFICANCE_TO_CATEGORY[value.lower()] = category


class ClinVarService:
    """Service for ClinVar annotations."""

    CLINVAR_VCF_URL = (
        "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz"
    )

    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        self.clinvar_dir = settings.clinvar_dir
        self.clinvar_file = self.clinvar_dir / "clinvar.vcf.gz"

    def is_loaded(self) -> bool:
        """Check if ClinVar data is loaded in database."""
        count = self.db.query(ClinVarAnnotation).limit(1).count()
        return count > 0

    def get_annotation_count(self) -> int:
        """Get total number of ClinVar annotations."""
        return self.db.query(ClinVarAnnotation).count()

    def lookup_variant(
        self,
        chromosome: str,
        position: int,
        reference: str,
        alternate: str,
    ) -> Optional[ClinVarAnnotation]:
        """Look up a variant in ClinVar."""
        # Normalize chromosome name
        chrom = chromosome.replace("chr", "")

        return (
            self.db.query(ClinVarAnnotation)
            .filter(
                ClinVarAnnotation.chromosome == chrom,
                ClinVarAnnotation.position == position,
                ClinVarAnnotation.reference == reference,
                ClinVarAnnotation.alternate == alternate,
            )
            .first()
        )

    def lookup_by_rsid(self, rsid: str) -> List[ClinVarAnnotation]:
        """Look up variants by rsID."""
        if not rsid.startswith("rs"):
            rsid = f"rs{rsid}"

        return (
            self.db.query(ClinVarAnnotation)
            .filter(ClinVarAnnotation.rsid == rsid)
            .all()
        )

    def lookup_by_gene(self, gene_symbol: str) -> List[ClinVarAnnotation]:
        """Look up all ClinVar entries for a gene."""
        return (
            self.db.query(ClinVarAnnotation)
            .filter(ClinVarAnnotation.gene_symbol == gene_symbol.upper())
            .all()
        )

    def get_pathogenic_variants(
        self,
        gene_symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[ClinVarAnnotation]:
        """Get pathogenic variants, optionally filtered by gene."""
        query = self.db.query(ClinVarAnnotation).filter(
            ClinVarAnnotation.clinical_significance.in_(
                ["Pathogenic", "Pathogenic/Likely_pathogenic", "Likely_pathogenic"]
            )
        )

        if gene_symbol:
            query = query.filter(ClinVarAnnotation.gene_symbol == gene_symbol.upper())

        return query.limit(limit).all()

    def categorize_significance(self, significance: str) -> str:
        """Categorize clinical significance into broad categories."""
        if not significance:
            return "unknown"

        sig_lower = significance.lower()
        return SIGNIFICANCE_TO_CATEGORY.get(sig_lower, "unknown")

    def load_variant_summary(
        self,
        filepath: Optional[str] = None,
        batch_size: int = 10000,
        assembly: str = "GRCh38",
    ) -> int:
        """
        Load ClinVar variant_summary.txt.gz file into database.

        This is the preferred format as it contains rsIDs for matching with VCF variants.

        Args:
            filepath: Path to variant_summary.txt.gz file
            batch_size: Number of records to commit at once
            assembly: Genome assembly to load (GRCh37 or GRCh38)

        Returns:
            Number of records loaded
        """
        if filepath is None:
            filepath = self.clinvar_dir / "variant_summary.txt.gz"

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(
                f"ClinVar variant summary not found at {filepath}. "
                f"Run: python scripts/download_clinvar.py"
            )

        logger.info(f"Loading ClinVar variant summary from {filepath}")
        logger.info(f"Filtering for assembly: {assembly}")

        count = 0
        skipped = 0
        batch = []

        open_func = gzip.open if str(filepath).endswith(".gz") else open

        with open_func(filepath, "rt", encoding="utf-8") as f:
            # Parse header to get column indices
            header = next(f).strip().split("\t")
            col_idx = {name: idx for idx, name in enumerate(header)}

            required_cols = [
                "AlleleID",
                "GeneSymbol",
                "ClinicalSignificance",
                "RS# (dbSNP)",
                "Assembly",
                "Chromosome",
                "PositionVCF",
                "ReferenceAlleleVCF",
                "AlternateAlleleVCF",
                "PhenotypeList",
                "ReviewStatus",
            ]

            for col in required_cols:
                if col not in col_idx:
                    logger.warning(f"Missing column: {col}")

            for line in f:
                parts = line.strip().split("\t")

                try:
                    # Only load specified assembly
                    line_assembly = (
                        parts[col_idx.get("Assembly", 0)]
                        if "Assembly" in col_idx
                        else ""
                    )
                    if assembly and line_assembly != assembly:
                        skipped += 1
                        continue

                    # Get rsID
                    rsid_raw = (
                        parts[col_idx.get("RS# (dbSNP)", 0)]
                        if "RS# (dbSNP)" in col_idx
                        else ""
                    )
                    if rsid_raw and rsid_raw != "-1" and rsid_raw != "-":
                        rsid = (
                            f"rs{rsid_raw}"
                            if not rsid_raw.startswith("rs")
                            else rsid_raw
                        )
                    else:
                        rsid = None

                    # Get position info
                    chrom = (
                        parts[col_idx.get("Chromosome", 0)]
                        if "Chromosome" in col_idx
                        else ""
                    )
                    pos_str = (
                        parts[col_idx.get("PositionVCF", 0)]
                        if "PositionVCF" in col_idx
                        else ""
                    )
                    ref = (
                        parts[col_idx.get("ReferenceAlleleVCF", 0)]
                        if "ReferenceAlleleVCF" in col_idx
                        else ""
                    )
                    alt = (
                        parts[col_idx.get("AlternateAlleleVCF", 0)]
                        if "AlternateAlleleVCF" in col_idx
                        else ""
                    )

                    # Skip if no position info
                    if not chrom or not pos_str or pos_str == "-1":
                        skipped += 1
                        continue

                    try:
                        pos = int(pos_str)
                    except ValueError:
                        skipped += 1
                        continue

                    # Get other fields
                    allele_id = (
                        parts[col_idx.get("AlleleID", 0)]
                        if "AlleleID" in col_idx
                        else ""
                    )
                    gene_symbol = (
                        parts[col_idx.get("GeneSymbol", 0)]
                        if "GeneSymbol" in col_idx
                        else ""
                    )
                    clinical_sig = (
                        parts[col_idx.get("ClinicalSignificance", 0)]
                        if "ClinicalSignificance" in col_idx
                        else ""
                    )
                    review_status = (
                        parts[col_idx.get("ReviewStatus", 0)]
                        if "ReviewStatus" in col_idx
                        else ""
                    )
                    phenotypes = (
                        parts[col_idx.get("PhenotypeList", 0)]
                        if "PhenotypeList" in col_idx
                        else ""
                    )
                    phenotype_ids = (
                        parts[col_idx.get("PhenotypeIDS", 0)]
                        if "PhenotypeIDS" in col_idx
                        else ""
                    )

                    annotation = ClinVarAnnotation(
                        chromosome=chrom,
                        position=pos,
                        reference=ref if ref != "na" else "",
                        alternate=alt if alt != "na" else "",
                        clinvar_id=allele_id,
                        rsid=rsid,
                        clinical_significance=clinical_sig,
                        review_status=review_status,
                        disease_names=phenotypes,
                        disease_ids=phenotype_ids,
                        gene_symbol=gene_symbol if gene_symbol else None,
                        last_updated=datetime.utcnow(),
                    )

                    batch.append(annotation)
                    count += 1

                    if len(batch) >= batch_size:
                        self.db.bulk_save_objects(batch)
                        self.db.commit()
                        batch = []
                        logger.info(f"Loaded {count} ClinVar records...")

                except Exception as e:
                    logger.warning(f"Error parsing line: {e}")
                    skipped += 1
                    continue

        # Save remaining batch
        if batch:
            self.db.bulk_save_objects(batch)
            self.db.commit()

        logger.info(f"Finished loading {count} ClinVar records (skipped {skipped})")
        return count

    def parse_and_load(
        self, vcf_path: Optional[str] = None, batch_size: int = 10000
    ) -> int:
        """
        Parse ClinVar VCF and load into database.

        Args:
            vcf_path: Path to ClinVar VCF file
            batch_size: Number of records to commit at once

        Returns:
            Number of records loaded
        """
        if vcf_path is None:
            vcf_path = self.clinvar_file

        vcf_path = Path(vcf_path)
        if not vcf_path.exists():
            raise FileNotFoundError(
                f"ClinVar VCF not found at {vcf_path}. "
                f"Download from {self.CLINVAR_VCF_URL}"
            )

        logger.info(f"Parsing ClinVar VCF from {vcf_path}")

        count = 0
        batch = []

        open_func = gzip.open if str(vcf_path).endswith(".gz") else open

        with open_func(vcf_path, "rt") as f:
            for line in f:
                if line.startswith("#"):
                    continue

                try:
                    annotation = self._parse_clinvar_line(line)
                    if annotation:
                        batch.append(annotation)
                        count += 1

                        if len(batch) >= batch_size:
                            self.db.bulk_save_objects(batch)
                            self.db.commit()
                            batch = []
                            logger.info(f"Loaded {count} ClinVar records...")

                except Exception as e:
                    logger.warning(f"Error parsing ClinVar line: {e}")
                    continue

        # Save remaining batch
        if batch:
            self.db.bulk_save_objects(batch)
            self.db.commit()

        logger.info(f"Finished loading {count} ClinVar records")
        return count

    def _parse_clinvar_line(self, line: str) -> Optional[ClinVarAnnotation]:
        """Parse a single line from ClinVar VCF."""
        parts = line.strip().split("\t")
        if len(parts) < 8:
            return None

        chrom = parts[0].replace("chr", "")
        try:
            pos = int(parts[1])
        except ValueError:
            return None

        ref = parts[3]
        alt = parts[4]

        # Handle multiple alternates
        if "," in alt:
            alt = alt.split(",")[0]

        # Parse INFO field
        info = {}
        for item in parts[7].split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info[key] = value

        # Extract ClinVar fields
        clinvar_id = info.get("ALLELEID", info.get("CLNHGVS", ""))
        rsid = parts[2] if parts[2] != "." else None

        clinical_sig = info.get("CLNSIG", "")
        review_status = info.get("CLNREVSTAT", "")

        # Disease info
        disease_names = info.get("CLNDN", "").replace("_", " ")
        disease_ids = info.get("CLNDISDB", "")

        # Gene
        gene_info = info.get("GENEINFO", "")
        gene_symbol = gene_info.split(":")[0] if gene_info else None

        return ClinVarAnnotation(
            chromosome=chrom,
            position=pos,
            reference=ref,
            alternate=alt,
            clinvar_id=clinvar_id,
            rsid=rsid,
            clinical_significance=clinical_sig,
            review_status=review_status,
            disease_names=disease_names,
            disease_ids=disease_ids,
            gene_symbol=gene_symbol,
            last_updated=datetime.utcnow(),
        )

    def get_disease_summary(self, diseases: str) -> List[Dict[str, str]]:
        """Parse disease names into structured format."""
        if not diseases:
            return []

        result = []
        for disease in diseases.split("|"):
            disease = disease.strip()
            if disease and disease.lower() != "not_provided":
                result.append(
                    {"name": disease, "formatted": disease.replace("_", " ").title()}
                )

        return result


def get_clinvar_service(db: Session) -> ClinVarService:
    """Get ClinVar service instance."""
    return ClinVarService(db)
