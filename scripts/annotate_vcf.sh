#!/bin/bash
#
# Annotate VCF files with SnpEff (adds gene symbols, consequences, impact, rsIDs)
# Usage: ./scripts/annotate_vcf.sh
#
# This will:
# 1. Download SnpEff if not present
# 2. Download the GRCh37.75 database
# 3. Annotate all VCF files in data/vcf/
# 4. Output annotated files as *.annotated.vcf.gz
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VCF_DIR="$PROJECT_DIR/data/vcf"
TOOLS_DIR="$PROJECT_DIR/tools"
SNPEFF_DIR="$TOOLS_DIR/snpEff"
SNPEFF_JAR="$SNPEFF_DIR/snpEff.jar"
SNPSIFT_JAR="$SNPEFF_DIR/SnpSift.jar"

# GRCh37 database (matches your DRAGEN reference)
GENOME_DB="GRCh37.75"

# SnpEff download URL
SNPEFF_URL="https://sourceforge.net/projects/snpeff/files/snpEff_latest_core.zip/download"

# --- Install SnpEff ---
install_snpeff() {
    if [ -f "$SNPEFF_JAR" ]; then
        echo "SnpEff already installed at $SNPEFF_JAR"
        return
    fi

    echo "Downloading SnpEff..."
    mkdir -p "$TOOLS_DIR"
    cd "$TOOLS_DIR"

    curl -L -o snpEff_latest_core.zip "$SNPEFF_URL"
    unzip -o snpEff_latest_core.zip
    rm snpEff_latest_core.zip

    echo "SnpEff installed."
}

# --- Download genome database ---
download_database() {
    echo "Checking SnpEff database for $GENOME_DB..."

    # Check if database already exists
    if [ -d "$SNPEFF_DIR/data/$GENOME_DB" ]; then
        echo "Database $GENOME_DB already downloaded."
        return
    fi

    echo "Downloading $GENOME_DB database (this may take a few minutes)..."
    java -jar "$SNPEFF_JAR" download "$GENOME_DB"
    echo "Database downloaded."
}

# --- Install bcftools via brew ---
install_bcftools() {
    if command -v bcftools &>/dev/null; then
        echo "bcftools already installed."
        return
    fi

    echo "Installing bcftools via Homebrew..."
    brew install bcftools
    echo "bcftools installed."
}

# --- Annotate a single VCF file ---
annotate_vcf() {
    local input_vcf="$1"
    local basename="$(basename "$input_vcf")"

    # Skip already-annotated files
    if [[ "$basename" == *".annotated."* ]]; then
        echo "Skipping already-annotated file: $basename"
        return
    fi

    local output_name="${basename%.vcf.gz}.annotated.vcf.gz"
    local output_vcf="$VCF_DIR/$output_name"

    if [ -f "$output_vcf" ]; then
        echo "Skipping $basename (annotated file already exists)"
        return
    fi

    echo ""
    echo "================================================"
    echo "Annotating: $basename"
    echo "================================================"

    # Run SnpEff
    echo "  Running SnpEff annotation..."
    java -Xmx4g -jar "$SNPEFF_JAR" \
        -v "$GENOME_DB" \
        -nodownload \
        -no-intergenic \
        -no-downstream \
        -no-upstream \
        -canon \
        -csvStats "$VCF_DIR/${basename%.vcf.gz}.stats.csv" \
        "$input_vcf" \
    | gzip > "$output_vcf"

    echo "  Output: $output_name"

    # Index if bcftools is available
    if command -v bcftools &>/dev/null; then
        echo "  Indexing..."
        bcftools index -t "$output_vcf" 2>/dev/null || true
    fi

    echo "  Done: $basename"
}

# --- Main ---
main() {
    echo "VCF Annotation Pipeline"
    echo "======================="
    echo "Project: $PROJECT_DIR"
    echo "VCF dir: $VCF_DIR"
    echo ""

    # Step 1: Install tools
    install_snpeff
    download_database
    install_bcftools

    echo ""
    echo "--- Annotating VCF files ---"

    # Step 2: Annotate SNP and indel VCFs (skip CNV/SV — SnpEff handles SNPs/indels)
    local count=0
    for vcf in "$VCF_DIR"/*.filtered.snp.vcf.gz "$VCF_DIR"/*.filtered.indel.vcf.gz; do
        [ -f "$vcf" ] || continue
        annotate_vcf "$vcf"
        count=$((count + 1))
    done

    if [ "$count" -eq 0 ]; then
        echo "No VCF files found to annotate in $VCF_DIR"
        exit 1
    fi

    echo ""
    echo "================================================"
    echo "Annotation complete!"
    echo "================================================"
    echo ""
    echo "Annotated files are in: $VCF_DIR/"
    ls -lh "$VCF_DIR"/*.annotated.vcf.gz 2>/dev/null
    echo ""
    echo "Next steps:"
    echo "  1. Go to Load Data in the dashboard"
    echo "  2. Load the new .annotated.vcf.gz files"
    echo "  3. The annotated variants will have gene symbols, consequences, and rsIDs"
}

main "$@"
