"""
AlphaGenome Dashboard - Server-Side Plot Generation

Uses AlphaGenome's visualization module + matplotlib to produce
publication-quality plots for variant analysis results.
"""

import io
import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

from backend.config import get_settings

logger = logging.getLogger(__name__)


def _ensure_plot_dir(variant_id: int) -> Path:
    """Ensure the plot directory exists for a variant."""
    plot_dir = get_settings().plots_dir / str(variant_id)
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir


def _save_figure(fig, variant_id: int, analysis_type: str) -> str:
    """Save a matplotlib figure and return the file path."""
    plot_dir = _ensure_plot_dir(variant_id)
    filename = f"{analysis_type}.png"
    filepath = plot_dir / filename
    fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(filepath)


def _fig_to_bytes(fig) -> bytes:
    """Convert a matplotlib figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def generate_track_overlay(
    ref_output,
    alt_output,
    output_type: str,
    variant_id: int,
) -> str:
    """
    Generate a REF vs ALT overlaid track plot using AlphaGenome's visualization.

    Returns the file path to the saved PNG.
    """
    try:
        from alphagenome.visualization import plot_components

        fig, ax = plt.subplots(figsize=(14, 4))
        plot_components.OverlaidTracks(
            reference=ref_output,
            alternate=alt_output,
            ax=ax,
        )
        ax.set_title(f"{output_type.replace('_', ' ')} — REF vs ALT")
        return _save_figure(fig, variant_id, output_type)
    except Exception as e:
        logger.error(f"Failed to generate track overlay for {output_type}: {e}")
        return ""


def generate_contact_map(
    ref_output,
    alt_output,
    variant_id: int,
    diff: bool = False,
) -> str:
    """
    Generate a contact map plot (or diff) using AlphaGenome's visualization.

    Returns the file path to the saved PNG.
    """
    try:
        from alphagenome.visualization import plot_components

        fig, ax = plt.subplots(figsize=(8, 8))
        if diff:
            plot_components.ContactMapsDiff(
                reference=ref_output,
                alternate=alt_output,
                ax=ax,
            )
            ax.set_title("Contact Map — ALT minus REF")
        else:
            plot_components.ContactMaps(
                output=ref_output,
                ax=ax,
            )
            ax.set_title("Contact Map — Reference")
        return _save_figure(fig, variant_id, f"CONTACT_MAPS{'_diff' if diff else ''}")
    except Exception as e:
        logger.error(f"Failed to generate contact map: {e}")
        return ""


def generate_sashimi_plot(
    ref_output,
    alt_output,
    variant_id: int,
) -> str:
    """
    Generate a sashimi plot for splice junction visualization.

    Returns the file path to the saved PNG.
    """
    try:
        from alphagenome.visualization import plot_components

        fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)
        plot_components.Sashimi(output=ref_output, ax=axes[0])
        axes[0].set_title("Reference — Splice Junctions")
        plot_components.Sashimi(output=alt_output, ax=axes[1])
        axes[1].set_title("Alternate — Splice Junctions")
        fig.tight_layout()
        return _save_figure(fig, variant_id, "SASHIMI")
    except Exception as e:
        logger.error(f"Failed to generate sashimi plot: {e}")
        return ""


def generate_ism_seqlogo(
    ism_matrix: dict,
    variant_id: int,
) -> str:
    """
    Generate an ISM sequence logo plot.

    Args:
        ism_matrix: Dict with keys 'positions', 'bases', 'values', 'reference_sequence'
        variant_id: Variant ID for file naming

    Returns the file path to the saved PNG.
    """
    try:
        from alphagenome.visualization import seqlogo

        fig, ax = plt.subplots(figsize=(16, 4))
        seqlogo.plot(
            values=ism_matrix.get("values", []),
            positions=ism_matrix.get("positions", []),
            bases=ism_matrix.get("bases", ["A", "C", "G", "T"]),
            ax=ax,
        )
        ax.set_title("In Silico Mutagenesis — Effect Landscape")
        return _save_figure(fig, variant_id, "ISM")
    except Exception as e:
        logger.error(f"Failed to generate ISM seqlogo: {e}")
        return ""


def generate_transcript_plot(
    interval,
    variant_id: int,
    gtf_data=None,
) -> str:
    """
    Generate a transcript annotation plot.

    Returns the file path to the saved PNG.
    """
    try:
        from alphagenome.visualization import plot_components

        fig, ax = plt.subplots(figsize=(14, 3))
        plot_components.TranscriptAnnotation(
            interval=interval,
            gtf=gtf_data,
            ax=ax,
        )
        ax.set_title("Transcript Annotation")
        return _save_figure(fig, variant_id, "TRANSCRIPT")
    except Exception as e:
        logger.error(f"Failed to generate transcript plot: {e}")
        return ""


def get_plot_path(variant_id: int, analysis_type: str) -> Optional[Path]:
    """Get the path to a saved plot, or None if it doesn't exist."""
    plot_dir = get_settings().plots_dir / str(variant_id)
    filepath = plot_dir / f"{analysis_type}.png"
    return filepath if filepath.exists() else None
