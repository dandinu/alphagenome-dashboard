"""
AlphaGenome Dashboard - AlphaGenome API Client

Wrapper around the AlphaGenome API for variant analysis.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Output types supported by AlphaGenome
OUTPUT_TYPES = {
    "RNA_SEQ": "RNA expression (667 tracks)",
    "CAGE": "TSS expression via CAGE (546 tracks)",
    "PROCAP": "TSS expression via PRO-CAP (12 tracks)",
    "DNASE": "Chromatin accessibility via DNase-seq (305 tracks)",
    "ATAC": "Chromatin accessibility via ATAC-seq (167 tracks)",
    "CHIP_HISTONE": "Histone modifications (1116 tracks)",
    "CHIP_TF": "Transcription factor binding (1617 tracks)",
    "SPLICE_SITES": "Splice site predictions (4 tracks)",
    "SPLICE_JUNCTIONS": "Splice junction usage (734 tracks)",
    "SPLICE_SITE_USAGE": "Splice site usage fraction (734 tracks)",
    "CONTACT_MAPS": "3D chromatin contacts (28 tracks)",
}

# Common tissue ontology terms
TISSUE_ONTOLOGY = {
    "liver": "UBERON:0002107",
    "heart": "UBERON:0000948",
    "brain": "UBERON:0000955",
    "kidney": "UBERON:0002113",
    "lung": "UBERON:0002048",
    "blood": "UBERON:0000178",
    "skin": "UBERON:0002097",
    "muscle": "UBERON:0001134",
    "intestine": "UBERON:0000160",
    "pancreas": "UBERON:0001264",
    "stomach": "UBERON:0000945",
    "spleen": "UBERON:0002106",
    "thyroid": "UBERON:0002046",
    "bone_marrow": "UBERON:0002371",
    "adipose": "UBERON:0001013",
}


@dataclass
class VariantInput:
    """Input variant for AlphaGenome analysis."""

    chromosome: str
    position: int  # 1-indexed (VCF format)
    reference: str
    alternate: str

    @property
    def interval_start(self) -> int:
        """Calculate interval start (0-indexed) for ~1MB window."""
        # Center the variant in a ~1MB window
        half_window = 524288  # 2^19
        return max(0, self.position - 1 - half_window)

    @property
    def interval_end(self) -> int:
        """Calculate interval end (0-indexed) for ~1MB window."""
        half_window = 524288
        return self.position - 1 + half_window


@dataclass
class AnalysisOutput:
    """Output from AlphaGenome analysis."""

    variant: VariantInput
    analysis_type: str
    score: Optional[float]
    score_details: Dict[str, Any]
    plot_data: Dict[str, Any]
    tracks_analyzed: int
    model_version: str
    analyzed_at: datetime


class AlphaGenomeClient:
    """Client for interacting with the AlphaGenome API."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.alphagenome_api_key
        self._model = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of the AlphaGenome model."""
        if self._initialized:
            return

        try:
            from alphagenome.models import dna_client

            self._model = dna_client.create(self.api_key)
            self._initialized = True
            logger.info("AlphaGenome client initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import alphagenome: {e}")
            raise RuntimeError(
                "AlphaGenome package not installed. "
                "Install with: pip install alphagenome"
            )
        except Exception as e:
            logger.error(f"Failed to initialize AlphaGenome client: {e}")
            raise

    def _create_variant(self, variant: VariantInput):
        """Create an alphagenome Variant object."""
        from alphagenome.data import genome

        return genome.Variant(
            chromosome=variant.chromosome,
            position=variant.position,  # 1-indexed
            reference_bases=variant.reference,
            alternate_bases=variant.alternate,
        )

    def _create_interval(self, variant: VariantInput):
        """Create an alphagenome Interval object."""
        from alphagenome.data import genome

        return genome.Interval(
            chromosome=variant.chromosome,
            start=variant.interval_start,
            end=variant.interval_end,
        )

    def _get_output_type(self, analysis_type: str):
        """Get the alphagenome OutputType enum value."""
        from alphagenome.models import dna_client

        return getattr(dna_client.OutputType, analysis_type)

    def predict_variant(
        self,
        variant: VariantInput,
        analysis_types: List[str] = None,
        ontology_terms: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Run prediction for a single variant.

        Args:
            variant: The variant to analyze
            analysis_types: List of output types (e.g., ["RNA_SEQ", "ATAC"])
            ontology_terms: Tissue/cell type ontology terms

        Returns:
            Dictionary containing predictions for REF and ALT alleles
        """
        self._ensure_initialized()

        if analysis_types is None:
            analysis_types = ["RNA_SEQ"]

        from alphagenome.models import dna_client

        ag_variant = self._create_variant(variant)
        ag_interval = self._create_interval(variant)

        requested_outputs = [self._get_output_type(at) for at in analysis_types]

        outputs = self._model.predict_variant(
            interval=ag_interval,
            variant=ag_variant,
            ontology_terms=ontology_terms,
            requested_outputs=requested_outputs,
        )

        return {
            "reference": outputs.reference,
            "alternate": outputs.alternate,
            "interval": ag_interval,
            "variant": ag_variant,
        }

    def score_variant(
        self,
        variant: VariantInput,
        analysis_types: List[str] = None,
        gene_symbol: Optional[str] = None,
    ) -> List[AnalysisOutput]:
        """
        Score a variant using recommended scorers.

        Args:
            variant: The variant to score
            analysis_types: Types of analysis to run
            gene_symbol: Gene symbol for gene-specific scoring

        Returns:
            List of AnalysisOutput objects
        """
        self._ensure_initialized()

        if analysis_types is None:
            analysis_types = ["RNA_SEQ", "SPLICE_SITES", "ATAC"]

        from alphagenome.models import variant_scorers

        ag_variant = self._create_variant(variant)

        results = []

        for analysis_type in analysis_types:
            try:
                # Get recommended scorers
                scorers = variant_scorers.get_recommended_scorers()

                # Score the variant
                scores = self._model.score_variant(
                    variant=ag_variant,
                )

                # Extract relevant score
                score_value = None
                score_details = {}

                if hasattr(scores, analysis_type.lower()):
                    score_data = getattr(scores, analysis_type.lower())
                    if hasattr(score_data, "values"):
                        score_value = float(score_data.values.mean())
                        score_details = {
                            "mean": float(score_data.values.mean()),
                            "max": float(score_data.values.max()),
                            "min": float(score_data.values.min()),
                            "std": float(score_data.values.std()),
                        }

                results.append(
                    AnalysisOutput(
                        variant=variant,
                        analysis_type=analysis_type,
                        score=score_value,
                        score_details=score_details,
                        plot_data={},  # Will be populated for visualization
                        tracks_analyzed=0,
                        model_version="alphagenome-v1",
                        analyzed_at=datetime.utcnow(),
                    )
                )

            except Exception as e:
                logger.error(f"Error scoring variant for {analysis_type}: {e}")
                results.append(
                    AnalysisOutput(
                        variant=variant,
                        analysis_type=analysis_type,
                        score=None,
                        score_details={"error": str(e)},
                        plot_data={},
                        tracks_analyzed=0,
                        model_version="alphagenome-v1",
                        analyzed_at=datetime.utcnow(),
                    )
                )

        return results

    def analyze_expression_impact(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze gene expression impact across tissues.

        Args:
            variant: The variant to analyze
            tissues: List of tissue names (will be converted to ontology terms)

        Returns:
            Expression impact analysis results
        """
        self._ensure_initialized()

        ontology_terms = None
        if tissues:
            ontology_terms = [
                TISSUE_ONTOLOGY.get(t.lower(), t)
                for t in tissues
                if t.lower() in TISSUE_ONTOLOGY or t.startswith("UBERON:")
            ]

        predictions = self.predict_variant(
            variant=variant,
            analysis_types=["RNA_SEQ"],
            ontology_terms=ontology_terms,
        )

        # Calculate log fold change
        ref_data = predictions["reference"].rna_seq
        alt_data = predictions["alternate"].rna_seq

        results = {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "tissues_analyzed": tissues or ["all"],
            "expression_changes": [],
        }

        # Process track-level data if available
        if hasattr(ref_data, "values") and hasattr(alt_data, "values"):
            ref_mean = float(ref_data.values.mean())
            alt_mean = float(alt_data.values.mean())

            import math

            log_fc = math.log(alt_mean + 0.001) - math.log(ref_mean + 0.001)

            results["summary"] = {
                "ref_expression": ref_mean,
                "alt_expression": alt_mean,
                "log_fold_change": log_fc,
                "direction": "increased" if log_fc > 0 else "decreased",
                "magnitude": abs(log_fc),
            }

        return results

    def analyze_splicing_impact(
        self,
        variant: VariantInput,
    ) -> Dict[str, Any]:
        """
        Analyze splicing impact of a variant.

        Args:
            variant: The variant to analyze

        Returns:
            Splicing impact analysis results
        """
        self._ensure_initialized()

        predictions = self.predict_variant(
            variant=variant,
            analysis_types=["SPLICE_SITES", "SPLICE_JUNCTIONS"],
        )

        results = {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "splice_site_impact": {},
            "splice_junction_impact": {},
        }

        # Analyze splice site changes
        if hasattr(predictions["reference"], "splice_sites"):
            ref_ss = predictions["reference"].splice_sites
            alt_ss = predictions["alternate"].splice_sites

            if hasattr(ref_ss, "values") and hasattr(alt_ss, "values"):
                ref_max = float(ref_ss.values.max())
                alt_max = float(alt_ss.values.max())

                results["splice_site_impact"] = {
                    "ref_max_probability": ref_max,
                    "alt_max_probability": alt_max,
                    "change": alt_max - ref_max,
                    "affects_splice_site": abs(alt_max - ref_max) > 0.1,
                }

        return results

    def get_available_outputs(self) -> Dict[str, str]:
        """Get available output types and descriptions."""
        return OUTPUT_TYPES.copy()

    def get_tissue_ontology(self) -> Dict[str, str]:
        """Get available tissue ontology mappings."""
        return TISSUE_ONTOLOGY.copy()


# Singleton instance
_client: Optional[AlphaGenomeClient] = None


def get_alphagenome_client() -> AlphaGenomeClient:
    """Get or create the AlphaGenome client instance."""
    global _client
    if _client is None:
        _client = AlphaGenomeClient()
    return _client
