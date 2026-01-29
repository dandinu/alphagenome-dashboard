#!/usr/bin/env python3
"""
Download ClinVar annotation data.

This script downloads the latest ClinVar variant summary file and processes it
for use with the AlphaGenome dashboard.
"""

import gzip
import os
import sys
from pathlib import Path
from urllib.request import urlretrieve

# ClinVar FTP URL
CLINVAR_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
)


def get_data_dir() -> Path:
    """Get the data directory path."""
    script_dir = Path(__file__).parent
    return script_dir.parent / "data" / "annotations" / "clinvar"


def download_clinvar():
    """Download ClinVar variant summary file."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    output_file = data_dir / "variant_summary.txt.gz"

    print(f"Downloading ClinVar data from:")
    print(f"  {CLINVAR_URL}")
    print(f"To: {output_file}")
    print()

    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\rDownloading: {percent}%")
        sys.stdout.flush()

    try:
        urlretrieve(CLINVAR_URL, output_file, reporthook=progress_hook)
        print("\n")
        print("Download complete!")

        # Count variants
        print("Processing file...")
        variant_count = 0
        with gzip.open(output_file, "rt", encoding="utf-8") as f:
            # Skip header
            next(f)
            for line in f:
                variant_count += 1
                if variant_count % 100000 == 0:
                    print(f"  Processed {variant_count:,} variants...")

        print(f"\nClinVar data loaded successfully!")
        print(f"  Total variants: {variant_count:,}")
        print(f"  File location: {output_file}")

    except Exception as e:
        print(f"\nError downloading ClinVar data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    download_clinvar()
