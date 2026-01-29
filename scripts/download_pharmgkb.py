#!/usr/bin/env python3
"""
Download PharmGKB annotation data.

This script downloads PharmGKB variant annotations for pharmacogenomics analysis.
Note: PharmGKB requires registration for bulk data access.
"""

import os
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

# PharmGKB downloads page (requires login for full data)
# Public data available at: https://www.pharmgkb.org/downloads
PHARMGKB_URL = "https://api.pharmgkb.org/v1/download/file/data/annotations.zip"


def get_data_dir() -> Path:
    """Get the data directory path."""
    script_dir = Path(__file__).parent
    return script_dir.parent / "data" / "annotations" / "pharmgkb"


def download_pharmgkb():
    """Download PharmGKB annotation data."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    zip_file = data_dir / "annotations.zip"

    print("PharmGKB Data Download")
    print("=" * 50)
    print()
    print("Note: PharmGKB requires registration for full bulk data access.")
    print("Visit https://www.pharmgkb.org/downloads to download data manually.")
    print()
    print("Required files:")
    print("  - var_drug_ann.tsv (Variant-Drug Annotations)")
    print("  - clinical_ann.tsv (Clinical Annotations)")
    print("  - genes.tsv (Gene Information)")
    print()
    print(f"Place downloaded files in: {data_dir}")
    print()

    # Try to download public annotations
    print("Attempting to download public annotations...")

    try:

        def progress_hook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\rDownloading: {percent}%")
            else:
                sys.stdout.write(f"\rDownloading: {count * block_size / 1024:.0f} KB")
            sys.stdout.flush()

        urlretrieve(PHARMGKB_URL, zip_file, reporthook=progress_hook)
        print("\n")

        # Extract zip file
        print("Extracting files...")
        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(data_dir)

        # Remove zip file
        zip_file.unlink()

        print("Download complete!")
        print(f"Files extracted to: {data_dir}")

        # List extracted files
        print("\nExtracted files:")
        for f in data_dir.iterdir():
            if f.is_file():
                size = f.stat().st_size
                print(f"  {f.name} ({size / 1024:.1f} KB)")

    except Exception as e:
        print(f"\nAutomatic download failed: {e}")
        print()
        print("Please download PharmGKB data manually:")
        print("1. Visit https://www.pharmgkb.org/downloads")
        print("2. Create a free account if needed")
        print("3. Download 'Variant Annotations' and 'Clinical Annotations'")
        print(f"4. Extract to: {data_dir}")


if __name__ == "__main__":
    download_pharmgkb()
