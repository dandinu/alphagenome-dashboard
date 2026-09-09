"""
AlphaGenome Dashboard - AlphaGenome Atlas Client

Wrapper around the AlphaGenome Atlas API (precomputed variant scores).
Provides AVI scores and feature attributions for SNVs, with batch lookup,
retry handling, and GRCh37->GRCh38 liftover.
"""

import logging
import time
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from backend.config import get_settings
from backend.services import genome_utils
from backend.services.alphagenome_client import VariantInput

logger = logging.getLogger(__name__)

AVI_SCORER = "AVI_SCORE"
AVI_FEATURE_SCORER = "AVI_SCORE_FEATURE_IMPORTANCE"

# Atlas feature-importance names grouped into the app's analysis modalities.
# Buckets mirror the deep-dive analyses available in the live client.
MODALITY_FEATURES = {
    "splicing": ["MERGED_SPLICING"],
    "expression": [
        "MAX_ABS_RNA_SEQ",
        "MAX_ABS_CAGE",
        "MAX_ABS_PROCAP",
        "MAX_ABS_POLYADENYLATION",
    ],
    "chromatin": ["MAX_ABS_ATAC", "MAX_ABS_DNASE", "MAX_ABS_CONTACT_MAPS"],
    "tf_binding": ["MAX_ABS_CHIP_TF"],
    "histone": ["MAX_ABS_CHIP_HISTONE"],
    "protein": ["ALPHAMISSENSE", "PROTEIN_TERMINATION", "START_LOST", "STOP_LOST"],
    "conservation": ["CACTUS_241_WAY", "PHASTCONS_470_WAY"],
}

# grpc status codes worth retrying
_RETRYABLE_CODES = ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED")


@dataclass
class AtlasResult:
    """Precomputed Atlas scores for a single SNV."""

    avi_score: float
    feature_importance: Dict[str, float]  # raw per-feature values
    modality_scores: Dict[str, float]  # summed |importance| per modality bucket
    attributions: Dict[str, float]  # modality shares, sum ~= 1
    top_modality: str
    atlas_version: str
    lifted_chromosome: str
    lifted_position: int
    retrieved_at: datetime = field(default_factory=datetime.utcnow)


class AtlasService:
    """Client for the AlphaGenome Atlas precomputed-score API."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.alphagenome_api_key
        self._client = None
        self._feature_names: Optional[List[str]] = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            from alphagenome.atlas import atlas
        except ImportError as e:
            logger.error(f"Failed to import alphagenome.atlas: {e}")
            raise RuntimeError(
                "AlphaGenome Atlas requires alphagenome>=0.9. "
                "Upgrade with: pip install -U alphagenome"
            )
        settings = get_settings()
        self._client = atlas.create(
            self.api_key, timeout=settings.atlas_timeout_seconds
        )
        self._initialized = True
        logger.info("AlphaGenome Atlas client initialized successfully")

    def _get_feature_names(self) -> List[str]:
        """Feature names for AVI_SCORE_FEATURE_IMPORTANCE columns, in order."""
        if self._feature_names is None:
            metadata = self._client.scorer_metadata()
            self._feature_names = list(
                metadata[AVI_FEATURE_SCORER].track_metadata["name"]
            )
        return self._feature_names

    # ------------------------------------------------------------------ #
    # Variant preparation
    # ------------------------------------------------------------------ #

    @staticmethod
    def _variant_key(chrom: str, pos: int, ref: str, alt: str) -> str:
        return f"{chrom}:{pos}:{ref}>{alt}"

    def _prepare_variant(self, variant: VariantInput):
        """Validate + liftover a VariantInput into an Atlas genome.Variant."""
        from alphagenome.data import genome

        genome_utils.validate_alleles(variant.reference, variant.alternate)
        if not genome_utils.is_snv(variant.reference, variant.alternate):
            raise ValueError(
                f"Atlas covers SNVs only ({variant.reference}>{variant.alternate}); "
                "use the live analysis endpoints for indels"
            )
        chrom, pos = genome_utils.liftover_position(
            variant.chromosome, variant.position
        )
        return genome.Variant(
            chromosome=chrom,
            position=pos,
            reference_bases=variant.reference,
            alternate_bases=variant.alternate,
        )

    # ------------------------------------------------------------------ #
    # Result parsing
    # ------------------------------------------------------------------ #

    def _build_result(
        self, avi_score: float, importances: List[float], chrom: str, pos: int
    ) -> AtlasResult:
        import alphagenome

        names = self._get_feature_names()
        feature_importance = {
            name: float(value) for name, value in zip(names, importances)
        }
        modality_scores = {
            modality: sum(abs(feature_importance.get(f, 0.0)) for f in features)
            for modality, features in MODALITY_FEATURES.items()
        }
        total = sum(modality_scores.values())
        attributions = {
            modality: (score / total if total > 0 else 0.0)
            for modality, score in modality_scores.items()
        }
        top_modality = max(attributions, key=attributions.get) if total > 0 else "none"
        return AtlasResult(
            avi_score=float(avi_score),
            feature_importance=feature_importance,
            modality_scores=modality_scores,
            attributions=attributions,
            top_modality=top_modality,
            atlas_version=f"atlas-sdk-{getattr(alphagenome, '__version__', 'unknown')}",
            lifted_chromosome=chrom,
            lifted_position=pos,
        )

    def _parse_scores(self, scores) -> Dict[str, AtlasResult]:
        """Map query results back to variants.

        query_variants does NOT preserve input order (it fans out over a
        thread pool), so results are keyed by the variant recorded in the
        AnnData obs metadata.
        """
        avi = scores[AVI_SCORER]
        features = scores[AVI_FEATURE_SCORER]

        feature_rows = {}
        for i, v in enumerate(features.obs["variant"]):
            key = self._variant_key(
                v.chromosome, v.position, v.reference_bases, v.alternate_bases
            )
            feature_rows[key] = list(features.X[i])

        results = {}
        for i, v in enumerate(avi.obs["variant"]):
            key = self._variant_key(
                v.chromosome, v.position, v.reference_bases, v.alternate_bases
            )
            results[key] = self._build_result(
                avi_score=avi.X[i][0],
                importances=feature_rows.get(key, []),
                chrom=v.chromosome,
                pos=v.position,
            )
        return results

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def _query_with_retry(self, ag_variants: list) -> Dict[str, AtlasResult]:
        """Query a chunk of prepared variants, retrying transient errors."""
        import grpc

        settings = get_settings()
        delay = 1.0
        last_error = None
        for attempt in range(settings.atlas_max_retries):
            try:
                if len(ag_variants) == 1:
                    scores = self._client.query_variant(
                        ag_variants[0],
                        requested_scorers=[AVI_SCORER, AVI_FEATURE_SCORER],
                    )
                else:
                    scores = self._client.query_variants(
                        ag_variants,
                        requested_scorers=[AVI_SCORER, AVI_FEATURE_SCORER],
                        progress_bar=False,
                    )
                return self._parse_scores(scores)
            except grpc.RpcError as e:
                code = e.code().name if e.code() else ""
                if code in _RETRYABLE_CODES and attempt < settings.atlas_max_retries - 1:
                    logger.warning(
                        f"Atlas query got {code}, retrying in {delay:.0f}s "
                        f"(attempt {attempt + 1})"
                    )
                    time.sleep(delay)
                    delay *= 4
                    last_error = e
                    continue
                raise
        raise last_error

    def lookup_variant(self, variant: VariantInput) -> AtlasResult:
        """Look up precomputed Atlas scores for a single SNV."""
        self._ensure_initialized()
        ag_variant = self._prepare_variant(variant)
        results = self._query_with_retry([ag_variant])
        key = self._variant_key(
            ag_variant.chromosome,
            ag_variant.position,
            ag_variant.reference_bases,
            ag_variant.alternate_bases,
        )
        if key not in results:
            raise ValueError(f"Atlas returned no scores for {key}")
        return results[key]

    def lookup_batch(
        self, variants: List[VariantInput]
    ) -> List[Union[AtlasResult, Exception]]:
        """Batch lookup. Returns one AtlasResult or Exception per input variant.

        A single invalid variant makes the underlying batch RPC fail, so a
        failed chunk falls back to per-variant queries to isolate bad inputs.
        """
        self._ensure_initialized()
        settings = get_settings()

        prepared = []  # (index, ag_variant, key) for valid inputs
        outputs: List[Union[AtlasResult, Exception]] = [None] * len(variants)
        for i, variant in enumerate(variants):
            try:
                ag_variant = self._prepare_variant(variant)
                key = self._variant_key(
                    ag_variant.chromosome,
                    ag_variant.position,
                    ag_variant.reference_bases,
                    ag_variant.alternate_bases,
                )
                prepared.append((i, ag_variant, key))
            except Exception as e:
                outputs[i] = e

        chunk_size = settings.atlas_batch_size
        for start in range(0, len(prepared), chunk_size):
            chunk = prepared[start : start + chunk_size]
            ag_variants = [p[1] for p in chunk]
            try:
                results = self._query_with_retry(ag_variants)
            except Exception as chunk_error:
                logger.warning(
                    f"Atlas chunk of {len(chunk)} failed "
                    f"({chunk_error}); retrying per-variant"
                )
                results = {}
                for _, ag_variant, key in chunk:
                    try:
                        results.update(self._query_with_retry([ag_variant]))
                    except Exception as e:
                        results[key] = e
            for i, _, key in chunk:
                outputs[i] = results.get(
                    key, ValueError(f"Atlas returned no scores for {key}")
                )
        return outputs


# Module-level singleton
_atlas_client: Optional[AtlasService] = None


def get_atlas_client() -> AtlasService:
    """Get the shared AtlasService instance."""
    global _atlas_client
    if _atlas_client is None:
        _atlas_client = AtlasService()
    return _atlas_client
