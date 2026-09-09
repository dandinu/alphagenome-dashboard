"""
AlphaGenome Dashboard - Shared genome utilities

Liftover and allele validation shared by the live AlphaGenome client
and the Atlas precomputed-score client.
"""

import re
import threading

from backend.config import get_settings

# Regex for symbolic alleles (CNVs, SVs, breakends)
SYMBOLIC_ALLELE_RE = re.compile(r"^<.*>$|^\]|^\[|.*\[|.*\]")

_liftover = None
_liftover_lock = threading.Lock()


def liftover_position(chrom: str, pos: int) -> tuple[str, int]:
    """Convert a GRCh37 position to GRCh38. Returns (chrom, pos_38).

    The position is expected in 1-based VCF coordinates. pyliftover
    uses 0-based coordinates internally. When the configured assembly
    is already GRCh38 the input is returned unchanged.
    """
    if get_settings().genome_assembly == "GRCh38":
        return chrom, pos

    global _liftover
    if _liftover is None:
        with _liftover_lock:
            if _liftover is None:
                from pyliftover import LiftOver

                _liftover = LiftOver("hg19", "hg38")

    result = _liftover.convert_coordinate(chrom, pos - 1)  # 0-based
    if not result:
        raise ValueError(
            f"Cannot lift over {chrom}:{pos} from GRCh37 to GRCh38 "
            "(position is unmapped in the chain file)"
        )
    return result[0][0], int(result[0][1]) + 1  # back to 1-based


def validate_alleles(reference: str, alternate: str) -> None:
    """Reject symbolic alleles (CNV/SV) that cannot be scored."""
    if SYMBOLIC_ALLELE_RE.match(alternate):
        raise ValueError(
            f"Symbolic alleles cannot be scored by AlphaGenome: "
            f"{alternate}. Only SNVs and short indels are supported."
        )
    if SYMBOLIC_ALLELE_RE.match(reference):
        raise ValueError(f"Symbolic reference allele cannot be scored: {reference}")


def is_snv(reference: str, alternate: str) -> bool:
    """True if the variant is a single-nucleotide substitution."""
    return (
        len(reference) == 1
        and len(alternate) == 1
        and reference.upper() in "ACGT"
        and alternate.upper() in "ACGT"
    )
