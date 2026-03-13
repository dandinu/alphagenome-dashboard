"""
AlphaGenome Dashboard - PharmGKB Annotation Service

Downloads and queries PharmGKB pharmacogenomics annotations.
"""

import os
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models.database import PharmGKBAnnotation

logger = logging.getLogger(__name__)

# Key pharmacogenes for analysis
PHARMACOGENES = {
    "CYP2D6": {
        "name": "Cytochrome P450 2D6",
        "function": "Drug metabolism enzyme",
        "drugs": [
            "codeine",
            "tramadol",
            "tamoxifen",
            "fluoxetine",
            "paroxetine",
            "risperidone",
        ],
    },
    "CYP2C19": {
        "name": "Cytochrome P450 2C19",
        "function": "Drug metabolism enzyme",
        "drugs": ["clopidogrel", "omeprazole", "escitalopram", "voriconazole"],
    },
    "CYP2C9": {
        "name": "Cytochrome P450 2C9",
        "function": "Drug metabolism enzyme",
        "drugs": ["warfarin", "phenytoin", "celecoxib", "losartan"],
    },
    "CYP3A4": {
        "name": "Cytochrome P450 3A4",
        "function": "Drug metabolism enzyme",
        "drugs": ["tacrolimus", "cyclosporine", "midazolam", "simvastatin"],
    },
    "CYP3A5": {
        "name": "Cytochrome P450 3A5",
        "function": "Drug metabolism enzyme",
        "drugs": ["tacrolimus"],
    },
    "VKORC1": {
        "name": "Vitamin K epoxide reductase complex subunit 1",
        "function": "Warfarin target",
        "drugs": ["warfarin"],
    },
    "SLCO1B1": {
        "name": "Solute carrier organic anion transporter 1B1",
        "function": "Drug transporter",
        "drugs": ["simvastatin", "atorvastatin", "pravastatin"],
    },
    "TPMT": {
        "name": "Thiopurine S-methyltransferase",
        "function": "Drug metabolism enzyme",
        "drugs": ["azathioprine", "mercaptopurine", "thioguanine"],
    },
    "DPYD": {
        "name": "Dihydropyrimidine dehydrogenase",
        "function": "Drug metabolism enzyme",
        "drugs": ["fluorouracil", "capecitabine"],
    },
    "UGT1A1": {
        "name": "UDP glucuronosyltransferase 1A1",
        "function": "Drug metabolism enzyme",
        "drugs": ["irinotecan", "atazanavir"],
    },
    "NUDT15": {
        "name": "Nudix hydrolase 15",
        "function": "Drug metabolism enzyme",
        "drugs": ["azathioprine", "mercaptopurine"],
    },
    "HLA-B": {
        "name": "Major histocompatibility complex class I B",
        "function": "Immune response",
        "drugs": ["carbamazepine", "allopurinol", "abacavir"],
    },
    "G6PD": {
        "name": "Glucose-6-phosphate dehydrogenase",
        "function": "Enzyme deficiency risk",
        "drugs": ["rasburicase", "primaquine"],
    },
    "IFNL3": {
        "name": "Interferon lambda 3",
        "function": "Drug response predictor",
        "drugs": ["peginterferon alfa-2a", "ribavirin"],
    },
    "CYP2B6": {
        "name": "Cytochrome P450 2B6",
        "function": "Drug metabolism enzyme",
        "drugs": ["efavirenz", "methadone"],
    },
}

# Level of evidence descriptions
EVIDENCE_LEVELS = {
    "1A": "Annotation for a variant-drug combination in a CPIC or DPWG guideline",
    "1B": "Variant-drug combination evaluated by PharmGKB expert",
    "2A": "Variant-drug combination with moderate clinical evidence",
    "2B": "Variant-drug combination with weak clinical evidence",
    "3": "Clinical annotations with low-level evidence",
    "4": "Clinical annotations based on case reports",
}


@dataclass
class PharmGKBVariant:
    """Structured PharmGKB variant information."""

    rsid: str
    gene: str
    alleles: List[str]
    drugs: List[Dict[str, Any]]
    evidence_level: str
    phenotype: Optional[str]
    recommendation: Optional[str]


class PharmGKBService:
    """Service for PharmGKB pharmacogenomics annotations."""

    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        self.pharmgkb_dir = settings.pharmgkb_dir

    def is_loaded(self) -> bool:
        """Check if PharmGKB data is loaded."""
        count = self.db.query(PharmGKBAnnotation).limit(1).count()
        return count > 0

    def get_annotation_count(self) -> int:
        """Get total PharmGKB annotations."""
        return self.db.query(PharmGKBAnnotation).count()

    def lookup_by_rsid(self, rsid: str) -> List[PharmGKBAnnotation]:
        """Look up annotations by rsID."""
        if not rsid.startswith("rs"):
            rsid = f"rs{rsid}"

        return (
            self.db.query(PharmGKBAnnotation)
            .filter(PharmGKBAnnotation.rsid == rsid)
            .all()
        )

    def lookup_by_gene(self, gene_symbol: str) -> List[PharmGKBAnnotation]:
        """Look up annotations for a gene."""
        return (
            self.db.query(PharmGKBAnnotation)
            .filter(PharmGKBAnnotation.gene_symbol == gene_symbol.upper())
            .all()
        )

    def lookup_by_drug(self, drug_name: str) -> List[PharmGKBAnnotation]:
        """Look up annotations for a drug."""
        return (
            self.db.query(PharmGKBAnnotation)
            .filter(PharmGKBAnnotation.drug_name.ilike(f"%{drug_name}%"))
            .all()
        )

    def get_pharmacogenes(self) -> Dict[str, Dict]:
        """Get dictionary of known pharmacogenes."""
        return PHARMACOGENES.copy()

    def get_gene_drug_associations(self, gene_symbol: str) -> List[Dict[str, Any]]:
        """Get all drug associations for a gene."""
        annotations = self.lookup_by_gene(gene_symbol)

        drugs = {}
        for ann in annotations:
            if ann.drug_name not in drugs:
                drugs[ann.drug_name] = {
                    "drug_name": ann.drug_name,
                    "drug_id": ann.drug_id,
                    "annotations": [],
                    "highest_evidence": None,
                }

            drugs[ann.drug_name]["annotations"].append(
                {
                    "rsid": ann.rsid,
                    "allele": ann.allele,
                    "phenotype": ann.phenotype_category,
                    "evidence": ann.level_of_evidence,
                    "text": ann.annotation_text,
                }
            )

            # Track highest evidence level
            if ann.level_of_evidence:
                current = drugs[ann.drug_name]["highest_evidence"]
                if current is None or ann.level_of_evidence < current:
                    drugs[ann.drug_name]["highest_evidence"] = ann.level_of_evidence

        return list(drugs.values())

    def get_actionable_variants(self, rsids: List[str]) -> List[PharmGKBAnnotation]:
        """Get actionable variants from a list of rsIDs."""
        # Filter to strong evidence levels
        return (
            self.db.query(PharmGKBAnnotation)
            .filter(
                PharmGKBAnnotation.rsid.in_(rsids),
                PharmGKBAnnotation.level_of_evidence.in_(["1A", "1B", "2A"]),
            )
            .all()
        )

    def generate_gene_report(
        self, gene_symbol: str, user_variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a pharmacogenomics report for a gene.

        Args:
            gene_symbol: Gene symbol (e.g., 'CYP2D6')
            user_variants: User's variants in this gene

        Returns:
            Gene report dictionary
        """
        gene_info = PHARMACOGENES.get(gene_symbol.upper(), {})
        annotations = self.lookup_by_gene(gene_symbol)
        drug_associations = self.get_gene_drug_associations(gene_symbol)

        report = {
            "gene_symbol": gene_symbol.upper(),
            "gene_name": gene_info.get("name", gene_symbol),
            "function": gene_info.get("function", "Unknown"),
            "user_variants": user_variants,
            "drugs": drug_associations,
            "recommendations": [],
            "risk_level": "normal",
        }

        # Match user variants to annotations
        user_rsids = {v.get("rsid") for v in user_variants if v.get("rsid")}

        for ann in annotations:
            if ann.rsid in user_rsids:
                if ann.level_of_evidence in ["1A", "1B"]:
                    report["recommendations"].append(
                        {
                            "drug": ann.drug_name,
                            "variant": ann.rsid,
                            "evidence": ann.level_of_evidence,
                            "text": ann.annotation_text,
                            "phenotype": ann.phenotype_category,
                        }
                    )

                    if ann.phenotype_category in ["Toxicity", "Poor metabolizer"]:
                        report["risk_level"] = "high"
                    elif report["risk_level"] == "normal":
                        report["risk_level"] = "moderate"

        return report

    def load_clinical_annotations(self, filepath: str, batch_size: int = 5000) -> int:
        """
        Load PharmGKB clinical annotations TSV file.

        Supports two formats:
        - clinicalVariants.tsv: columns variant, gene, type, level of evidence, chemicals, phenotypes
        - var_drug_ann.tsv: columns Variant/Haplotypes, Gene, Drug(s), Level of Evidence, etc.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"PharmGKB file not found: {filepath}")

        count = 0
        batch = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                try:
                    # Support both clinicalVariants.tsv and var_drug_ann.tsv column names
                    variant_id = (
                        row.get("variant")
                        or row.get("Variant/Haplotypes")
                        or row.get("rsid", "")
                    )
                    gene = (
                        row.get("gene")
                        or row.get("Gene", "")
                    )
                    drug = (
                        row.get("chemicals")
                        or row.get("Drug(s)")
                        or row.get("drug", "")
                    )
                    evidence = (
                        row.get("level of evidence")
                        or row.get("Level of Evidence", "")
                    )
                    phenotype = (
                        row.get("type")
                        or row.get("Phenotype Category", "")
                    )
                    phenotypes_detail = row.get("phenotypes", "")

                    # clinicalVariants.tsv may have multiple chemicals separated by commas/semicolons
                    # Create one record per drug for proper matching
                    drugs = [d.strip() for d in drug.replace(";", ",").split(",") if d.strip()] or [""]

                    for drug_name in drugs:
                        ann = PharmGKBAnnotation(
                            rsid=variant_id,
                            gene_symbol=gene,
                            drug_name=drug_name,
                            drug_id=row.get("Chemical ID", ""),
                            phenotype_category=phenotype,
                            significance=row.get("Significance", ""),
                            level_of_evidence=evidence,
                            annotation_text=(
                                row.get("Annotation Text")
                                or row.get("Sentence")
                                or phenotypes_detail
                                or ""
                            ),
                            guideline_name=row.get("Guideline", ""),
                            allele=row.get("Alleles", ""),
                        )

                        batch.append(ann)
                        count += 1

                        if len(batch) >= batch_size:
                            self.db.bulk_save_objects(batch)
                            self.db.commit()
                            batch = []
                            logger.info(f"Loaded {count} PharmGKB records...")

                except Exception as e:
                    logger.warning(f"Error parsing PharmGKB row: {e}")
                    continue

        if batch:
            self.db.bulk_save_objects(batch)
            self.db.commit()

        logger.info(f"Finished loading {count} PharmGKB records")
        return count

    def get_evidence_description(self, level: str) -> str:
        """Get description for evidence level."""
        return EVIDENCE_LEVELS.get(level, "Unknown evidence level")


def get_pharmgkb_service(db: Session) -> PharmGKBService:
    """Get PharmGKB service instance."""
    return PharmGKBService(db)
