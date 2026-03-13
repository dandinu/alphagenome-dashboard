"""
AlphaGenome Dashboard - AlphaGenome API Client

Wrapper around the AlphaGenome API for variant analysis.
Supports liftover (GRCh37->GRCh38), all 7 specialized variant scorers,
epigenomic analysis (histone/TF/3D contacts), ISM, and composite splicing scoring.
"""

import logging
import re
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

# Regex for symbolic alleles (CNVs, SVs, breakends)
_SYMBOLIC_ALLELE_RE = re.compile(r"^<.*>$|^\]|^\[|.*\[|.*\]")


# Supported model sequence lengths (must be exact)
SUPPORTED_LENGTHS = [16384, 131072, 524288, 1048576]
DEFAULT_LENGTH = 524288


@dataclass
class VariantInput:
    """Input variant for AlphaGenome analysis."""

    chromosome: str
    position: int  # 1-indexed (VCF format)
    reference: str
    alternate: str

    @property
    def interval_start(self) -> int:
        """Calculate interval start (0-indexed) for a supported-length window."""
        return _compute_interval(self.position)[0]

    @property
    def interval_end(self) -> int:
        """Calculate interval end (0-indexed) for a supported-length window."""
        return _compute_interval(self.position)[1]


def _compute_interval(position_1based: int, length: int = DEFAULT_LENGTH) -> tuple[int, int]:
    """Compute a (start, end) interval of exactly `length` bp centered on position.

    If centering would put start < 0, the window is shifted right so start == 0.
    """
    center_0based = position_1based - 1
    half = length // 2
    start = center_0based - half
    if start < 0:
        start = 0
    end = start + length
    return start, end


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
        self._liftover = None  # lazy-loaded LiftOver object

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

    # ------------------------------------------------------------------ #
    # Liftover (GRCh37 -> GRCh38)
    # ------------------------------------------------------------------ #

    def _liftover_position(self, chrom: str, pos: int) -> tuple[str, int]:
        """Convert a GRCh37 position to GRCh38. Returns (chrom, pos_38).

        The position is expected in 1-based VCF coordinates. pyliftover
        uses 0-based coordinates internally.
        """
        if get_settings().genome_assembly == "GRCh38":
            return chrom, pos

        if self._liftover is None:
            from pyliftover import LiftOver
            self._liftover = LiftOver("hg19", "hg38")

        result = self._liftover.convert_coordinate(chrom, pos - 1)  # 0-based
        if not result:
            raise ValueError(
                f"Cannot lift over {chrom}:{pos} from GRCh37 to GRCh38 "
                "(position is unmapped in the chain file)"
            )
        return result[0][0], int(result[0][1]) + 1  # back to 1-based

    @staticmethod
    def _validate_alleles(variant: VariantInput) -> None:
        """Reject symbolic alleles (CNV/SV) that cannot be scored."""
        if _SYMBOLIC_ALLELE_RE.match(variant.alternate):
            raise ValueError(
                f"Symbolic alleles cannot be scored by AlphaGenome: "
                f"{variant.alternate}. Only SNVs and short indels are supported."
            )
        if _SYMBOLIC_ALLELE_RE.match(variant.reference):
            raise ValueError(
                f"Symbolic reference allele cannot be scored: {variant.reference}"
            )

    # ------------------------------------------------------------------ #
    # AlphaGenome object builders
    # ------------------------------------------------------------------ #

    def _create_variant(self, variant: VariantInput):
        """Create an alphagenome Variant object with liftover applied."""
        from alphagenome.data import genome

        self._validate_alleles(variant)
        chrom, pos = self._liftover_position(variant.chromosome, variant.position)

        return genome.Variant(
            chromosome=chrom,
            position=pos,  # 1-indexed, now in GRCh38
            reference_bases=variant.reference,
            alternate_bases=variant.alternate,
        )

    def _create_interval(self, variant: VariantInput):
        """Create an alphagenome Interval object with liftover applied."""
        from alphagenome.data import genome

        chrom, pos = self._liftover_position(variant.chromosome, variant.position)
        start, end = _compute_interval(pos)

        return genome.Interval(
            chromosome=chrom,
            start=start,
            end=end,
        )

    def _get_output_type(self, analysis_type: str):
        """Get the alphagenome OutputType enum value."""
        from alphagenome.models import dna_client

        return getattr(dna_client.OutputType, analysis_type)

    # ------------------------------------------------------------------ #
    # Prediction
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Variant scoring – all 7 specialized scorers
    # ------------------------------------------------------------------ #

    def score_variant_detailed(
        self,
        variant: VariantInput,
        gene_symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Score a variant using all 7 specialized AlphaGenome scorers.

        Returns a dict keyed by scorer name with tidy DataFrames and raw scores.
        """
        self._ensure_initialized()

        from alphagenome.models import variant_scorers, dna_client

        OT = dna_client.OutputType
        AT = variant_scorers.AggregationType

        ag_variant = self._create_variant(variant)
        ag_interval = self._create_interval(variant)

        # Build all scorers with their required constructor arguments
        scorer_defs = [
            ("center_mask", lambda: variant_scorers.CenterMaskScorer(
                requested_output=OT.RNA_SEQ, width=None, aggregation_type=AT.DIFF_MEAN)),
            ("gene_mask_lfc", lambda: variant_scorers.GeneMaskLFCScorer(
                requested_output=OT.RNA_SEQ)),
            ("gene_mask_active", lambda: variant_scorers.GeneMaskActiveScorer(
                requested_output=OT.RNA_SEQ)),
            ("gene_mask_splicing", lambda: variant_scorers.GeneMaskSplicingScorer(
                requested_output=OT.SPLICE_SITES, width=None)),
            ("splice_junction", lambda: variant_scorers.SpliceJunctionScorer()),
            ("polyadenylation", lambda: variant_scorers.PolyadenylationScorer()),
            ("contact_map", lambda: variant_scorers.ContactMapScorer()),
        ]

        # Try to score all at once first (most efficient)
        all_scorers = []
        scorer_names = []
        for name, factory in scorer_defs:
            try:
                all_scorers.append(factory())
                scorer_names.append(name)
            except Exception as e:
                logger.warning(f"Failed to create scorer {name}: {e}")

        results = {name: {"summary": {}, "tidy": []} for name, _ in scorer_defs}

        # Map our scorer names to the class name prefix used in variant_scorer column
        class_name_map = {
            "center_mask": "CenterMaskScorer",
            "gene_mask_lfc": "GeneMaskLFCScorer",
            "gene_mask_active": "GeneMaskActiveScorer",
            "gene_mask_splicing": "GeneMaskSplicingScorer",
            "splice_junction": "SpliceJunctionScorer",
            "polyadenylation": "PolyadenylationScorer",
            "contact_map": "ContactMapScorer",
        }

        try:
            raw_scores = self._model.score_variant(
                interval=ag_interval,
                variant=ag_variant,
                variant_scorers=all_scorers,
            )

            tidy_df = variant_scorers.tidy_scores(raw_scores)
            if tidy_df is not None and not tidy_df.empty and "raw_score" in tidy_df.columns:
                for name in scorer_names:
                    cls_name = class_name_map.get(name, name)
                    if "variant_scorer" in tidy_df.columns:
                        mask = tidy_df["variant_scorer"].str.startswith(cls_name, na=False)
                        subset = tidy_df[mask]
                    else:
                        subset = tidy_df

                    if not subset.empty:
                        results[name] = {
                            "summary": {
                                "mean": float(subset["raw_score"].mean()),
                                "max": float(subset["raw_score"].max()),
                                "min": float(subset["raw_score"].min()),
                                "std": float(subset["raw_score"].std()),
                                "n_tracks": len(subset),
                            },
                            "tidy": subset.head(100).to_dict(orient="records"),
                        }

        except Exception as e:
            logger.error(f"Batch scoring failed, falling back to individual scorers: {e}")
            for name, factory in scorer_defs:
                try:
                    scorer = factory()
                    raw = self._model.score_variant(
                        interval=ag_interval,
                        variant=ag_variant,
                        variant_scorers=[scorer],
                    )
                    tidy_df = variant_scorers.tidy_scores(raw)
                    if tidy_df is not None and not tidy_df.empty and "raw_score" in tidy_df.columns:
                        results[name] = {
                            "summary": {
                                "mean": float(tidy_df["raw_score"].mean()),
                                "max": float(tidy_df["raw_score"].max()),
                                "min": float(tidy_df["raw_score"].min()),
                                "std": float(tidy_df["raw_score"].std()),
                                "n_tracks": len(tidy_df),
                            },
                            "tidy": tidy_df.head(100).to_dict(orient="records"),
                        }
                except Exception as e2:
                    logger.warning(f"Scorer {name} failed individually: {e2}")
                    results[name] = {"summary": {}, "tidy": [], "error": str(e2)}

        return results

    def compute_composite_splicing_score(
        self, detailed_scores: Dict[str, Any]
    ) -> Optional[float]:
        """
        Compute the composite splicing score using the documented formula:
        alphagenome_splicing = max(splice_sites) + max(splice_site_usage) + max(splice_junctions) / 5.0
        """
        try:
            splice_sites_max = detailed_scores.get("gene_mask_splicing", {}).get("summary", {}).get("max")
            splice_junction_max = detailed_scores.get("splice_junction", {}).get("summary", {}).get("max")

            if splice_sites_max is None and splice_junction_max is None:
                return None

            ss = abs(splice_sites_max) if splice_sites_max is not None else 0.0
            sj = abs(splice_junction_max) if splice_junction_max is not None else 0.0

            # The formula combines splice_sites + splice_site_usage + splice_junctions/5
            # gene_mask_splicing scorer covers both SPLICE_SITES and SPLICE_SITE_USAGE
            return ss + sj / 5.0
        except Exception as e:
            logger.warning(f"Failed to compute composite splicing score: {e}")
            return None

    def score_variant(
        self,
        variant: VariantInput,
        analysis_types: List[str] = None,
        gene_symbol: Optional[str] = None,
    ) -> List[AnalysisOutput]:
        """
        Score a variant using specialized scorers and return per-analysis-type results.

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

        # Run all 7 specialized scorers once
        detailed_scores = self.score_variant_detailed(variant, gene_symbol)
        composite_splicing = self.compute_composite_splicing_score(detailed_scores)

        # Map analysis types to relevant scorer results
        scorer_mapping = {
            "RNA_SEQ": ["center_mask", "gene_mask_lfc"],
            "CAGE": ["center_mask", "gene_mask_lfc"],
            "PROCAP": ["center_mask"],
            "DNASE": ["center_mask"],
            "ATAC": ["center_mask"],
            "CHIP_HISTONE": ["center_mask"],
            "CHIP_TF": ["center_mask"],
            "SPLICE_SITES": ["gene_mask_splicing"],
            "SPLICE_JUNCTIONS": ["splice_junction"],
            "SPLICE_SITE_USAGE": ["gene_mask_splicing"],
            "CONTACT_MAPS": ["contact_map"],
        }

        results = []
        for analysis_type in analysis_types:
            relevant_scorers = scorer_mapping.get(analysis_type, ["center_mask"])
            score_details = {}
            best_score = None

            for scorer_name in relevant_scorers:
                scorer_data = detailed_scores.get(scorer_name, {})
                summary = scorer_data.get("summary", {})
                if summary:
                    score_details[scorer_name] = summary
                    scorer_max = summary.get("max")
                    if scorer_max is not None:
                        if best_score is None or abs(scorer_max) > abs(best_score):
                            best_score = scorer_max

            # Include composite splicing for splicing-related types
            if analysis_type in ("SPLICE_SITES", "SPLICE_JUNCTIONS", "SPLICE_SITE_USAGE"):
                score_details["composite_splicing_score"] = composite_splicing

            results.append(
                AnalysisOutput(
                    variant=variant,
                    analysis_type=analysis_type,
                    score=best_score,
                    score_details=score_details,
                    plot_data={},
                    tracks_analyzed=sum(
                        s.get("summary", {}).get("n_tracks", 0)
                        for s in (detailed_scores.get(sn, {}) for sn in relevant_scorers)
                    ),
                    model_version="alphagenome-v1",
                    analyzed_at=datetime.utcnow(),
                )
            )

        return results

    # ------------------------------------------------------------------ #
    # Expression analysis
    # ------------------------------------------------------------------ #

    def analyze_expression_impact(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
    ) -> Dict[str, Any]:
        """Analyze gene expression impact across tissues."""
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

    # ------------------------------------------------------------------ #
    # Splicing analysis
    # ------------------------------------------------------------------ #

    def analyze_splicing_impact(
        self,
        variant: VariantInput,
    ) -> Dict[str, Any]:
        """Analyze splicing impact of a variant with composite scoring."""
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
            "composite_splicing_score": None,
        }

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

        # Also compute detailed scores and composite
        detailed = self.score_variant_detailed(variant)
        results["composite_splicing_score"] = self.compute_composite_splicing_score(detailed)

        return results

    # ------------------------------------------------------------------ #
    # Epigenomic analysis (Step 3)
    # ------------------------------------------------------------------ #

    def analyze_histone_impact(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze histone modification impact of a variant.

        Compares REF vs ALT predictions for histone marks across tissues.
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
            analysis_types=["CHIP_HISTONE"],
            ontology_terms=ontology_terms,
        )

        ref_data = predictions["reference"].chip_histone
        alt_data = predictions["alternate"].chip_histone

        results = {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "tissues_analyzed": tissues or ["all"],
            "histone_marks": {},
            "summary": {},
        }

        if hasattr(ref_data, "values") and hasattr(alt_data, "values"):
            import numpy as np

            ref_vals = ref_data.values
            alt_vals = alt_data.values
            diff = alt_vals - ref_vals

            # Overall summary
            results["summary"] = {
                "max_change": float(np.abs(diff).max()),
                "mean_change": float(diff.mean()),
                "n_tracks_affected": int((np.abs(diff) > 0.1).sum()),
                "n_tracks_total": int(diff.size),
            }

            # Per-mark analysis for known histone marks
            known_marks = ["H3K27ac", "H3K4me3", "H3K36me3", "H3K27me3", "H3K9ac"]
            if hasattr(ref_data, "track_names"):
                track_names = ref_data.track_names
                for mark in known_marks:
                    mark_indices = [
                        i for i, name in enumerate(track_names) if mark in name
                    ]
                    if mark_indices:
                        mark_ref = ref_vals[..., mark_indices].mean()
                        mark_alt = alt_vals[..., mark_indices].mean()
                        change = float(mark_alt - mark_ref)
                        results["histone_marks"][mark] = {
                            "ref_signal": float(mark_ref),
                            "alt_signal": float(mark_alt),
                            "change": change,
                            "direction": "increased" if change > 0 else "decreased",
                            "significant": abs(change) > 0.1,
                            "n_tracks": len(mark_indices),
                        }

        return results

    def analyze_tf_binding(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
        significance_threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Analyze transcription factor binding impact of a variant.

        Compares REF vs ALT for TF binding predictions and filters to
        significantly affected TFs.
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
            analysis_types=["CHIP_TF"],
            ontology_terms=ontology_terms,
        )

        ref_data = predictions["reference"].chip_tf
        alt_data = predictions["alternate"].chip_tf

        results = {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "tissues_analyzed": tissues or ["all"],
            "disrupted_tfs": [],
            "created_tfs": [],
            "summary": {},
        }

        if hasattr(ref_data, "values") and hasattr(alt_data, "values"):
            import numpy as np

            ref_vals = ref_data.values
            alt_vals = alt_data.values
            diff = alt_vals - ref_vals

            results["summary"] = {
                "max_change": float(np.abs(diff).max()),
                "mean_change": float(diff.mean()),
                "n_tfs_affected": int((np.abs(diff) > significance_threshold).sum()),
                "n_tfs_total": int(diff.shape[-1]) if diff.ndim > 1 else int(diff.size),
            }

            if hasattr(ref_data, "track_names"):
                track_names = ref_data.track_names
                # Get per-track max magnitude changes
                if diff.ndim > 1:
                    track_max_diff = diff.max(axis=tuple(range(diff.ndim - 1)))
                    track_min_diff = diff.min(axis=tuple(range(diff.ndim - 1)))
                else:
                    track_max_diff = diff
                    track_min_diff = diff

                for i, tf_name in enumerate(track_names):
                    max_d = float(track_max_diff[i]) if i < len(track_max_diff) else 0
                    min_d = float(track_min_diff[i]) if i < len(track_min_diff) else 0
                    peak_change = max_d if abs(max_d) > abs(min_d) else min_d

                    if abs(peak_change) > significance_threshold:
                        tf_entry = {
                            "tf_name": tf_name,
                            "peak_change": peak_change,
                            "direction": "gained" if peak_change > 0 else "lost",
                        }
                        if peak_change > 0:
                            results["created_tfs"].append(tf_entry)
                        else:
                            results["disrupted_tfs"].append(tf_entry)

                # Sort by magnitude
                results["disrupted_tfs"].sort(key=lambda x: abs(x["peak_change"]), reverse=True)
                results["created_tfs"].sort(key=lambda x: abs(x["peak_change"]), reverse=True)

        return results

    def analyze_3d_contacts(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze 3D chromatin contact changes caused by a variant.

        Uses CONTACT_MAPS output type and ContactMapScorer for scoring.
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
            analysis_types=["CONTACT_MAPS"],
            ontology_terms=ontology_terms,
        )

        ref_data = predictions["reference"].contact_maps
        alt_data = predictions["alternate"].contact_maps

        results = {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "tissues_analyzed": tissues or ["all"],
            "contact_changes": {},
            "summary": {},
        }

        if hasattr(ref_data, "values") and hasattr(alt_data, "values"):
            import numpy as np

            ref_vals = ref_data.values
            alt_vals = alt_data.values
            diff = alt_vals - ref_vals

            results["summary"] = {
                "max_change": float(np.abs(diff).max()),
                "mean_change": float(diff.mean()),
                "contact_score_change": float(np.abs(diff).sum()),
            }

            # ContactMapScorer result
            from alphagenome.models import variant_scorers

            ag_variant = self._create_variant(variant)
            ag_interval = self._create_interval(variant)
            try:
                scorer = variant_scorers.ContactMapScorer()
                contact_scores = self._model.score_variant(
                    interval=ag_interval,
                    variant=ag_variant,
                    variant_scorers=[scorer],
                )
                tidy = variant_scorers.tidy_scores(contact_scores)
                if not tidy.empty and "score" in tidy.columns:
                    results["contact_changes"] = {
                        "scorer_max": float(tidy["score"].max()),
                        "scorer_mean": float(tidy["score"].mean()),
                        "n_affected_contacts": int((tidy["score"].abs() > 0.05).sum()),
                        "details": tidy.to_dict(orient="records")[:50],  # top 50
                    }
            except Exception as e:
                logger.warning(f"ContactMapScorer failed: {e}")
                results["contact_changes"]["error"] = str(e)

        return results

    # ------------------------------------------------------------------ #
    # In Silico Mutagenesis (Step 4)
    # ------------------------------------------------------------------ #

    def run_ism(
        self,
        variant: VariantInput,
        output_types: List[str] = None,
        window_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Run in silico mutagenesis around a variant position.

        Generates all SNVs in a window around the variant, scores each,
        and builds a (position x base) effect matrix for visualization.

        Args:
            variant: The variant to analyze
            output_types: Output types to score (default: RNA_SEQ)
            window_size: Number of bases on each side of the variant

        Returns:
            ISM results including the effect matrix
        """
        self._ensure_initialized()

        if output_types is None:
            output_types = ["RNA_SEQ"]

        from alphagenome.interpretation import ism

        ag_variant = self._create_variant(variant)
        ag_interval = self._create_interval(variant)

        requested_outputs = [self._get_output_type(ot) for ot in output_types]

        # Generate all SNVs in the window
        ism_variants = ism.ism_variants(
            interval=ag_interval,
            variant=ag_variant,
            window_size=window_size,
        )

        # Score each ISM variant
        ism_scores = []
        for ism_var in ism_variants:
            try:
                score = self._model.score_variant(variant=ism_var)
                ism_scores.append(score)
            except Exception as e:
                logger.warning(f"ISM scoring failed for variant: {e}")
                ism_scores.append(None)

        # Build effect matrix
        try:
            matrix = ism.ism_matrix(
                ism_variants=ism_variants,
                ism_scores=ism_scores,
            )
            matrix_data = {
                "positions": matrix.positions.tolist() if hasattr(matrix, "positions") else [],
                "bases": matrix.bases.tolist() if hasattr(matrix, "bases") else ["A", "C", "G", "T"],
                "values": matrix.values.tolist() if hasattr(matrix, "values") else [],
                "reference_sequence": matrix.reference_sequence if hasattr(matrix, "reference_sequence") else "",
            }
        except Exception as e:
            logger.warning(f"ISM matrix construction failed: {e}")
            matrix_data = {"error": str(e)}

        return {
            "variant": {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
            },
            "window_size": window_size,
            "output_types": output_types,
            "n_variants_scored": sum(1 for s in ism_scores if s is not None),
            "matrix": matrix_data,
        }

    # ------------------------------------------------------------------ #
    # Full analysis (runs everything)
    # ------------------------------------------------------------------ #

    def run_full_analysis(
        self,
        variant: VariantInput,
        tissues: List[str] = None,
        gene_symbol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run all available analyses on a variant.

        Returns a combined result dict with all analysis types.
        """
        self._ensure_initialized()

        all_analysis_types = [
            "RNA_SEQ", "SPLICE_SITES", "SPLICE_JUNCTIONS", "ATAC",
            "DNASE", "CHIP_HISTONE", "CHIP_TF", "CONTACT_MAPS",
        ]

        results = {
            "scoring": [],
            "expression": None,
            "splicing": None,
            "histone": None,
            "tf_binding": None,
            "contacts": None,
        }

        # Scoring with all types
        try:
            results["scoring"] = self.score_variant(
                variant=variant,
                analysis_types=all_analysis_types,
                gene_symbol=gene_symbol,
            )
        except Exception as e:
            logger.error(f"Full analysis scoring failed: {e}")

        # Expression
        try:
            results["expression"] = self.analyze_expression_impact(variant, tissues)
        except Exception as e:
            logger.error(f"Expression analysis failed: {e}")

        # Splicing
        try:
            results["splicing"] = self.analyze_splicing_impact(variant)
        except Exception as e:
            logger.error(f"Splicing analysis failed: {e}")

        # Histone
        try:
            results["histone"] = self.analyze_histone_impact(variant, tissues)
        except Exception as e:
            logger.error(f"Histone analysis failed: {e}")

        # TF binding
        try:
            results["tf_binding"] = self.analyze_tf_binding(variant, tissues)
        except Exception as e:
            logger.error(f"TF binding analysis failed: {e}")

        # 3D contacts
        try:
            results["contacts"] = self.analyze_3d_contacts(variant, tissues)
        except Exception as e:
            logger.error(f"3D contacts analysis failed: {e}")

        return results

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

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
