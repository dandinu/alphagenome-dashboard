"""
AlphaGenome Dashboard - VCF Parser Service

Parses VCF files and extracts variant information with focus on coding variants.
"""

import os
import gzip
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator, Tuple
from dataclasses import dataclass

from backend.config import get_settings

logger = logging.getLogger(__name__)

# Coding consequences that indicate a variant affects protein coding
CODING_CONSEQUENCES = {
    # High impact
    "transcript_ablation",
    "splice_acceptor_variant",
    "splice_donor_variant",
    "stop_gained",
    "frameshift_variant",
    "stop_lost",
    "start_lost",
    "transcript_amplification",
    # Moderate impact
    "inframe_insertion",
    "inframe_deletion",
    "missense_variant",
    "protein_altering_variant",
    # Low impact
    "splice_region_variant",
    "incomplete_terminal_codon_variant",
    "start_retained_variant",
    "stop_retained_variant",
    "synonymous_variant",
    # Also include these for comprehensive coverage
    "coding_sequence_variant",
    "5_prime_UTR_variant",
    "3_prime_UTR_variant",
}

IMPACT_LEVELS = {
    "transcript_ablation": "HIGH",
    "splice_acceptor_variant": "HIGH",
    "splice_donor_variant": "HIGH",
    "stop_gained": "HIGH",
    "frameshift_variant": "HIGH",
    "stop_lost": "HIGH",
    "start_lost": "HIGH",
    "transcript_amplification": "HIGH",
    "inframe_insertion": "MODERATE",
    "inframe_deletion": "MODERATE",
    "missense_variant": "MODERATE",
    "protein_altering_variant": "MODERATE",
    "splice_region_variant": "LOW",
    "incomplete_terminal_codon_variant": "LOW",
    "start_retained_variant": "LOW",
    "stop_retained_variant": "LOW",
    "synonymous_variant": "LOW",
    "coding_sequence_variant": "LOW",
    "5_prime_UTR_variant": "MODIFIER",
    "3_prime_UTR_variant": "MODIFIER",
    "intron_variant": "MODIFIER",
    "intergenic_variant": "MODIFIER",
}


@dataclass
class ParsedVariant:
    """Represents a parsed variant from VCF."""

    chromosome: str
    position: int
    rsid: Optional[str]
    reference: str
    alternate: str
    quality: Optional[float]
    filter_status: str
    genotype: Optional[str]
    zygosity: Optional[str]
    variant_type: str
    is_coding: bool
    is_annotated: bool  # Whether variant has VEP/SnpEff annotations
    gene_symbol: Optional[str]
    gene_id: Optional[str]
    transcript_id: Optional[str]
    consequence: Optional[str]
    impact: Optional[str]
    protein_change: Optional[str]
    codon_change: Optional[str]
    af_gnomad: Optional[float]
    af_1000g: Optional[float]
    raw_info: Dict[str, Any]


class VCFParser:
    """Parser for VCF files with support for various annotation formats."""

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.sample_name: Optional[str] = None
        self.header_lines: List[str] = []
        self.info_fields: Dict[str, Dict] = {}
        self.format_fields: Dict[str, Dict] = {}
        self._is_gzipped = str(filepath).endswith(".gz")

    def _open_file(self):
        """Open VCF file handling gzip compression."""
        if self._is_gzipped:
            return gzip.open(self.filepath, "rt")
        return open(self.filepath, "r")

    def _parse_header(self, file_handle) -> str:
        """Parse VCF header and return first data line."""
        for line in file_handle:
            if line.startswith("##INFO="):
                self._parse_info_header(line)
            elif line.startswith("##FORMAT="):
                self._parse_format_header(line)
            elif line.startswith("#CHROM"):
                # Column header line
                parts = line.strip().split("\t")
                if len(parts) > 9:
                    self.sample_name = parts[9]
                self.header_lines.append(line)
                return next(file_handle, None)
            else:
                self.header_lines.append(line)
        return None

    def _parse_info_header(self, line: str):
        """Parse INFO field metadata from header."""
        # Example: ##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
        try:
            content = line.split("=<")[1].rstrip(">\n")
            fields = {}
            for part in content.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    fields[key] = value.strip('"')
            if "ID" in fields:
                self.info_fields[fields["ID"]] = fields
        except Exception:
            pass

    def _parse_format_header(self, line: str):
        """Parse FORMAT field metadata from header."""
        try:
            content = line.split("=<")[1].rstrip(">\n")
            fields = {}
            for part in content.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    fields[key] = value.strip('"')
            if "ID" in fields:
                self.format_fields[fields["ID"]] = fields
        except Exception:
            pass

    def _parse_info_field(self, info_str: str) -> Dict[str, Any]:
        """Parse INFO column into dictionary."""
        info = {}
        if info_str == "." or not info_str:
            return info

        for item in info_str.split(";"):
            if "=" in item:
                key, value = item.split("=", 1)
                info[key] = value
            else:
                info[item] = True
        return info

    def _parse_genotype(
        self, format_str: str, sample_str: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Parse genotype from FORMAT and sample columns."""
        if not format_str or not sample_str:
            return None, None

        format_fields = format_str.split(":")
        sample_values = sample_str.split(":")

        gt_idx = format_fields.index("GT") if "GT" in format_fields else -1
        if gt_idx == -1 or gt_idx >= len(sample_values):
            return None, None

        genotype = sample_values[gt_idx]

        # Determine zygosity
        if "/" in genotype:
            alleles = genotype.split("/")
        elif "|" in genotype:
            alleles = genotype.split("|")
        else:
            return genotype, None

        if "." in alleles:
            zygosity = "unknown"
        elif alleles[0] == alleles[1]:
            if alleles[0] == "0":
                zygosity = "homozygous_ref"
            else:
                zygosity = "homozygous_alt"
        else:
            zygosity = "heterozygous"

        return genotype, zygosity

    def _determine_variant_type(self, ref: str, alt: str) -> str:
        """Determine the type of variant."""
        # Handle symbolic alleles (e.g. <DEL>, <DUP>, <INS>, <INV>, <DUP:TANDEM>)
        if alt.startswith("<") and alt.endswith(">"):
            sym = alt[1:-1].split(":")[0].upper()
            if sym in ("DEL", "DUP", "INS", "INV", "CNV"):
                return sym
            return "SV"

        # Handle breakend notation (e.g. ]13:123456]T or T[13:123456[)
        if "[" in alt or "]" in alt:
            return "BND"

        if len(ref) == 1 and len(alt) == 1:
            return "SNP"
        elif len(ref) > len(alt):
            return "DEL"
        elif len(ref) < len(alt):
            return "INS"
        else:
            return "MNP"

    def _extract_vep_annotation(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract VEP/SnpEff annotations from INFO field."""
        result = {
            "gene_symbol": None,
            "gene_id": None,
            "transcript_id": None,
            "consequence": None,
            "impact": None,
            "protein_change": None,
            "codon_change": None,
        }

        # Try CSQ field (VEP)
        if "CSQ" in info:
            csq = info["CSQ"].split(",")[0]  # Take first annotation
            parts = csq.split("|")
            if len(parts) > 3:
                result["consequence"] = parts[1] if len(parts) > 1 else None
                result["impact"] = parts[2] if len(parts) > 2 else None
                result["gene_symbol"] = parts[3] if len(parts) > 3 else None
                result["gene_id"] = parts[4] if len(parts) > 4 else None
                result["transcript_id"] = parts[6] if len(parts) > 6 else None
                if len(parts) > 11:
                    result["protein_change"] = parts[11]
                if len(parts) > 10:
                    result["codon_change"] = parts[10]

        # Try ANN field (SnpEff)
        elif "ANN" in info:
            ann = info["ANN"].split(",")[0]
            parts = ann.split("|")
            if len(parts) > 3:
                result["consequence"] = parts[1] if len(parts) > 1 else None
                result["impact"] = parts[2] if len(parts) > 2 else None
                result["gene_symbol"] = parts[3] if len(parts) > 3 else None
                result["gene_id"] = parts[4] if len(parts) > 4 else None
                result["transcript_id"] = parts[6] if len(parts) > 6 else None
                if len(parts) > 10:
                    result["protein_change"] = parts[10]
                if len(parts) > 9:
                    result["codon_change"] = parts[9]

        # Try GENEINFO field (common in dbSNP/ClinVar VCFs)
        elif "GENEINFO" in info:
            gene_info = info["GENEINFO"]
            if ":" in gene_info:
                result["gene_symbol"] = gene_info.split(":")[0]

        # If we have consequence, determine impact
        if result["consequence"] and not result["impact"]:
            consequences = result["consequence"].split("&")
            for csq in consequences:
                if csq in IMPACT_LEVELS:
                    result["impact"] = IMPACT_LEVELS[csq]
                    break

        return result

    def _extract_frequencies(
        self, info: Dict[str, Any]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Extract population allele frequencies."""
        af_gnomad = None
        af_1000g = None

        # gnomAD frequencies
        for key in ["gnomAD_AF", "AF_gnomad", "gnomADg_AF", "gnomADe_AF", "AF_popmax"]:
            if key in info:
                try:
                    af_gnomad = float(info[key])
                    break
                except (ValueError, TypeError):
                    pass

        # 1000 Genomes frequencies
        for key in ["1000G_AF", "AF_1000g", "AF", "CAF"]:
            if key in info:
                try:
                    value = info[key]
                    if "," in str(value):
                        value = value.split(",")[1]  # Take ALT frequency
                    af_1000g = float(value)
                    break
                except (ValueError, TypeError):
                    pass

        return af_gnomad, af_1000g

    def _is_coding_variant(
        self, consequence: Optional[str], gene_symbol: Optional[str]
    ) -> bool:
        """Determine if variant is coding based on consequence."""
        if not consequence:
            # If no annotation but has gene symbol, consider it potentially coding
            return gene_symbol is not None

        consequences = consequence.split("&")
        return any(csq in CODING_CONSEQUENCES for csq in consequences)

    def _is_annotated(self, info: Dict[str, Any]) -> bool:
        """Check if variant has any annotation data (VEP, SnpEff, or GENEINFO)."""
        return any(key in info for key in ["CSQ", "ANN", "GENEINFO"])

    def _parse_line(self, line: str) -> Optional[ParsedVariant]:
        """Parse a single VCF data line."""
        parts = line.strip().split("\t")
        if len(parts) < 8:
            return None

        chrom = parts[0]
        try:
            pos = int(parts[1])
        except ValueError:
            return None

        rsid = parts[2] if parts[2] != "." else None
        ref = parts[3]
        alt = parts[4]

        # Handle multiple alternates - take first for now
        if "," in alt:
            alt = alt.split(",")[0]

        try:
            qual = float(parts[5]) if parts[5] != "." else None
        except ValueError:
            qual = None

        filter_status = parts[6]

        # Parse INFO
        info = self._parse_info_field(parts[7])

        # Parse genotype
        genotype, zygosity = None, None
        if len(parts) > 9:
            genotype, zygosity = self._parse_genotype(parts[8], parts[9])

        # Skip homozygous reference variants
        if zygosity == "homozygous_ref":
            return None

        # Extract annotations
        annotations = self._extract_vep_annotation(info)
        af_gnomad, af_1000g = self._extract_frequencies(info)

        # Determine variant type
        variant_type = self._determine_variant_type(ref, alt)

        # Check if variant has annotations
        is_annotated = self._is_annotated(info)

        # Determine if coding
        is_coding = self._is_coding_variant(
            annotations["consequence"], annotations["gene_symbol"]
        )

        return ParsedVariant(
            chromosome=chrom,
            position=pos,
            rsid=rsid,
            reference=ref,
            alternate=alt,
            quality=qual,
            filter_status=filter_status,
            genotype=genotype,
            zygosity=zygosity,
            variant_type=variant_type,
            is_coding=is_coding,
            is_annotated=is_annotated,
            gene_symbol=annotations["gene_symbol"],
            gene_id=annotations["gene_id"],
            transcript_id=annotations["transcript_id"],
            consequence=annotations["consequence"],
            impact=annotations["impact"],
            protein_change=annotations["protein_change"],
            codon_change=annotations["codon_change"],
            af_gnomad=af_gnomad,
            af_1000g=af_1000g,
            raw_info=info,
        )

    def parse(self, coding_only: bool = True) -> Generator[ParsedVariant, None, None]:
        """
        Parse VCF file and yield variants.

        Args:
            coding_only: If True, only yield coding variants

        Yields:
            ParsedVariant objects
        """
        with self._open_file() as f:
            first_data_line = self._parse_header(f)

            if first_data_line:
                variant = self._parse_line(first_data_line)
                if variant and (not coding_only or variant.is_coding):
                    yield variant

            for line in f:
                if line.startswith("#"):
                    continue

                variant = self._parse_line(line)
                if variant and (not coding_only or variant.is_coding):
                    yield variant

    def count_variants(self) -> Tuple[int, int, int]:
        """Count total, coding, and annotated variants in file.

        Returns:
            Tuple of (total_count, coding_count, annotated_count)
        """
        total = 0
        coding = 0
        annotated = 0

        with self._open_file() as f:
            for line in f:
                if line.startswith("#"):
                    continue

                variant = self._parse_line(line)
                if variant:
                    total += 1
                    if variant.is_coding:
                        coding += 1
                    if variant.is_annotated:
                        annotated += 1

        return total, coding, annotated


def discover_vcf_files() -> List[Dict[str, Any]]:
    """Discover VCF files in the data directory."""
    settings = get_settings()
    vcf_dir = settings.vcf_data_dir

    files = []
    for ext in ["*.vcf", "*.vcf.gz"]:
        for filepath in vcf_dir.glob(ext):
            stat = filepath.stat()
            files.append(
                {
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

    return sorted(files, key=lambda x: x["modified"], reverse=True)
