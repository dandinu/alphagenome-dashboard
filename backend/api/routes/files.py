"""
AlphaGenome Dashboard - Files API Routes

Endpoints for VCF file discovery and loading.
"""

import logging
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import VCFFile, Variant, VCFFileResponse, VCFFileList
from backend.services import VCFParser, discover_vcf_files
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=List[dict])
async def list_vcf_files():
    """
    List all VCF files available in the data directory.
    Returns files found in data/vcf/ folder.
    """
    files = discover_vcf_files()
    return files


@router.get("/loaded", response_model=VCFFileList)
async def list_loaded_files(db: Session = Depends(get_db)):
    """List VCF files that have been loaded into the database."""
    files = db.query(VCFFile).all()
    return VCFFileList(
        files=[VCFFileResponse.model_validate(f) for f in files], total=len(files)
    )


@router.post("/{filename}/parse", response_model=VCFFileResponse)
async def parse_vcf_file(
    filename: str,
    background_tasks: BackgroundTasks,
    coding_only: bool = False,  # Changed default to False to load all variants
    limit: Optional[int] = None,  # Limit number of variants to load
    skip_count: bool = True,  # Skip counting phase for large files (faster)
    db: Session = Depends(get_db),
):
    """
    Parse a VCF file and load variants into the database.

    Args:
        filename: Name of the VCF file in data/vcf/
        coding_only: Only load coding variants (default: False, loads all variants)
        limit: Maximum number of variants to load (optional, useful for large files)
        skip_count: Skip variant counting phase for faster loading (default: True)
    """
    settings = get_settings()
    filepath = settings.vcf_data_dir / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"VCF file not found: {filename}")

    # Check if already loaded
    existing = db.query(VCFFile).filter(VCFFile.filename == filename).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"File already loaded. Delete first to reload. ID: {existing.id}",
        )

    try:
        # Parse VCF
        parser = VCFParser(str(filepath))

        # Count variants (skip if skip_count is True for large files)
        if skip_count:
            # Use limit as estimate or 0 if unknown
            total_count = limit if limit else 0
            coding_count = 0
            annotated_count = 0
        else:
            total_count, coding_count, annotated_count = parser.count_variants()

        # Create file record
        vcf_file = VCFFile(
            filename=filename,
            filepath=str(filepath),
            sample_name=None,  # Will be updated during parsing
            total_variants=total_count,
            coding_variants=coding_count,
            annotated_variants=annotated_count,
        )
        db.add(vcf_file)
        db.commit()
        db.refresh(vcf_file)

        # Load variants in background
        background_tasks.add_task(
            _load_variants_task, vcf_file.id, str(filepath), coding_only, limit
        )

        return VCFFileResponse.model_validate(vcf_file)

    except Exception as e:
        logger.error(f"Error parsing VCF file {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_vcf_file(file_id: int, db: Session = Depends(get_db)):
    """Delete a loaded VCF file and its variants."""
    vcf_file = db.query(VCFFile).filter(VCFFile.id == file_id).first()
    if not vcf_file:
        raise HTTPException(status_code=404, detail="File not found")

    db.delete(vcf_file)
    db.commit()

    return {"status": "deleted", "filename": vcf_file.filename}


@router.get("/{file_id}", response_model=VCFFileResponse)
async def get_vcf_file(file_id: int, db: Session = Depends(get_db)):
    """Get details of a loaded VCF file."""
    vcf_file = db.query(VCFFile).filter(VCFFile.id == file_id).first()
    if not vcf_file:
        raise HTTPException(status_code=404, detail="File not found")

    return VCFFileResponse.model_validate(vcf_file)


@router.get("/{file_id}/status")
async def get_parse_status(file_id: int, db: Session = Depends(get_db)):
    """Get the parsing status of a VCF file."""
    vcf_file = db.query(VCFFile).filter(VCFFile.id == file_id).first()
    if not vcf_file:
        raise HTTPException(status_code=404, detail="File not found")

    loaded_count = db.query(Variant).filter(Variant.vcf_file_id == file_id).count()

    return {
        "file_id": file_id,
        "filename": vcf_file.filename,
        "total_variants": vcf_file.total_variants,
        "coding_variants": vcf_file.coding_variants,
        "loaded_variants": loaded_count,
        "status": "complete" if loaded_count >= vcf_file.coding_variants else "loading",
    }


def _load_variants_task(
    file_id: int, filepath: str, coding_only: bool, limit: Optional[int] = None
):
    """Background task to load variants from VCF.

    Args:
        file_id: Database ID of the VCF file record
        filepath: Path to the VCF file
        coding_only: Only load coding variants
        limit: Maximum number of variants to load (optional)
    """
    from backend.db import SessionLocal

    db = SessionLocal()
    try:
        parser = VCFParser(filepath)
        batch = []
        batch_size = 5000
        count = 0

        for parsed in parser.parse(coding_only=coding_only):
            variant = Variant(
                vcf_file_id=file_id,
                chromosome=parsed.chromosome,
                position=parsed.position,
                rsid=parsed.rsid,
                reference=parsed.reference,
                alternate=parsed.alternate,
                quality=parsed.quality,
                filter_status=parsed.filter_status,
                genotype=parsed.genotype,
                zygosity=parsed.zygosity,
                variant_type=parsed.variant_type,
                is_coding=parsed.is_coding,
                is_annotated=parsed.is_annotated,
                gene_symbol=parsed.gene_symbol,
                gene_id=parsed.gene_id,
                transcript_id=parsed.transcript_id,
                consequence=parsed.consequence,
                impact=parsed.impact,
                protein_change=parsed.protein_change,
                codon_change=parsed.codon_change,
                af_gnomad=parsed.af_gnomad,
                af_1000g=parsed.af_1000g,
            )
            batch.append(variant)
            count += 1

            if len(batch) >= batch_size:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
                logger.info(f"Loaded {count} variants for file {file_id}")

            # Check if we've reached the limit
            if limit and count >= limit:
                logger.info(f"Reached limit of {limit} variants for file {file_id}")
                break

        if batch:
            db.bulk_save_objects(batch)
            db.commit()

        # Update file record with actual counts
        vcf_file = db.query(VCFFile).filter(VCFFile.id == file_id).first()
        if vcf_file:
            # Update sample name if found
            if parser.sample_name:
                vcf_file.sample_name = parser.sample_name

            # Update variant counts from loaded data
            vcf_file.total_variants = count
            vcf_file.coding_variants = (
                db.query(Variant)
                .filter(Variant.vcf_file_id == file_id, Variant.is_coding == True)
                .count()
            )
            vcf_file.annotated_variants = (
                db.query(Variant)
                .filter(Variant.vcf_file_id == file_id, Variant.is_annotated == True)
                .count()
            )
            db.commit()

        logger.info(f"Finished loading {count} variants for file {file_id}")

    except Exception as e:
        logger.error(f"Error loading variants: {e}")
    finally:
        db.close()
