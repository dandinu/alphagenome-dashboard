# AGENTS.md - Coding Agent Guidelines

This document provides guidelines for AI coding agents working on the AlphaGenome Dashboard project.

## Project Overview

A personal genome analysis dashboard using Google DeepMind's AlphaGenome API, with ClinVar and PharmGKB annotations. Stack: FastAPI backend (Python), React frontend (TypeScript), SQLite database.

### Data
- **Genome assembly**: GRCh37 (configured in `backend/config.py` as `genome_assembly`)
- **VCF files**: Personal WGS data in `data/vcf/` — 4 files (SNP, indel, CNV, SV), ~4.8M variants total
- **VCFs are unannotated**: No rsIDs (all `.`), no VEP/SnpEff gene annotations. ClinVar/PharmGKB matching uses position-based lookup (chr + pos + ref + alt) as the primary strategy, with rsID as a bonus when available.
- **CNV/SV files use symbolic alleles**: `<DEL>`, `<DUP>`, `<DUP:TANDEM>`, `<INS>`, `<INV>`, and breakend notation (`]chr:pos]`). The VCF parser handles these in `_determine_variant_type()`.
- **Raw data**: `RAW/` contains source BAM/FASTQ/VCF files (~82GB). Gitignored. Only VCFs are copied to `data/vcf/` for the app.
- **Annotations**: `data/annotations/clinvar/variant_summary.txt.gz` and PharmGKB data. ClinVar is loaded filtered to GRCh37.

## Build & Run Commands

### Full Application
```bash
# Install all dependencies
npm install

# Start both backend and frontend (recommended)
npm start

# Backend only (http://localhost:8000)
npm run backend
# Or directly:
PYTHONPATH=. uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Frontend only (http://localhost:5173)
npm run frontend
```

### Frontend (React/TypeScript)
```bash
cd frontend

npm run dev      # Development server
npm run build    # Production build (runs tsc -b && vite build)
npm run lint     # ESLint
npm run preview  # Preview production build
```

### Backend (Python/FastAPI)
```bash
# Install dependencies
pip install -r requirements.txt

# Run server (from project root)
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000

# Run a single Python file
PYTHONPATH=. python backend/services/vcf_parser.py

# Test a specific module
PYTHONPATH=. python -c "from backend.services import VCFParser; print('OK')"
```

### Database
```bash
# Recreate database schema
PYTHONPATH=. python -c "from backend.db.database import Base, engine; Base.metadata.create_all(bind=engine)"

# Delete and recreate
rm -f data/alphagenome.db && PYTHONPATH=. python -c "from backend.db.database import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Data Scripts
```bash
python scripts/download_clinvar.py   # Download ClinVar annotations
python scripts/download_pharmgkb.py  # Download PharmGKB annotations
```

### Loading Data via API
Once the backend is running, load VCFs and annotations through the API:
```bash
# List discovered VCF files
curl http://localhost:8000/api/files

# Parse a VCF file (runs in background)
curl -X POST "http://localhost:8000/api/files/60820188476500.filtered.snp.vcf.gz/parse?coding_only=false"

# Load ClinVar with GRCh37 (matches our genome assembly)
curl -X POST "http://localhost:8000/api/annotations/clinvar/load?assembly=GRCh37"

# Check loading progress
curl http://localhost:8000/api/files/loaded
curl http://localhost:8000/api/annotations/clinvar/status
```

## Code Style Guidelines

### Python (Backend)

**Imports** - Group in order: stdlib, third-party, local. Use absolute imports from `backend`:
```python
import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import Variant, VariantResponse
from backend.services import get_clinvar_service
```

**Type Hints** - Always use type hints for function signatures:
```python
def parse_vcf(filepath: str, coding_only: bool = True) -> List[ParsedVariant]:
    ...

async def get_variant(variant_id: int, db: Session = Depends(get_db)) -> VariantResponse:
    ...
```

**Naming Conventions**:
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`
- File names: `snake_case.py`

**Docstrings** - Use triple quotes for modules and public functions:
```python
"""
AlphaGenome Dashboard - VCF Parser Service

Parses VCF files and extracts variant information.
"""

def parse_variant(line: str) -> Optional[ParsedVariant]:
    """Parse a single VCF data line.
    
    Args:
        line: Raw VCF line string
        
    Returns:
        ParsedVariant object or None if invalid
    """
```

**Error Handling** - Use HTTPException for API errors, logging for internal errors:
```python
if not variant:
    raise HTTPException(status_code=404, detail="Variant not found")

try:
    result = client.score_variant(variant_input)
except Exception as e:
    logger.error(f"Error scoring variant: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

**Pydantic Models** - Define in `backend/models/schemas.py`:
```python
class VariantResponse(BaseModel):
    id: int
    chromosome: str
    position: int
    rsid: Optional[str]
    
    class Config:
        from_attributes = True  # For SQLAlchemy model conversion
```

**SQLAlchemy Models** - Define in `backend/models/database.py`:
```python
class Variant(Base):
    __tablename__ = "variants"
    
    id = Column(Integer, primary_key=True, index=True)
    chromosome = Column(String(10), index=True)
    position = Column(Integer, index=True)
```

### TypeScript (Frontend)

**Imports** - Group: React, third-party, local components, types, styles:
```typescript
import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Bell } from 'lucide-react';

import Header from '../components/layout/Header';
import { variantsApi } from '../services/api';
import type { Variant, VariantFilters } from '../types';
```

**Component Structure** - Use functional components with explicit prop types:
```typescript
interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="...">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </header>
  );
}
```

**Naming Conventions**:
- Components: `PascalCase.tsx`
- Hooks: `useCamelCase.ts`
- Utils/services: `camelCase.ts`
- Types: `PascalCase` (interfaces and types)

**API Calls** - Use the api service in `frontend/src/services/api.ts`:
```typescript
const { data, isLoading } = useQuery({
  queryKey: ['variants', page, filters],
  queryFn: () => variantsApi.list(page, pageSize, filters),
});
```

**Styling** - Use Tailwind CSS classes. Prefer utility classes:
```typescript
<div className="flex items-center gap-4 rounded-lg border border-gray-200 p-4">
```

## Project Structure

```
backend/
├── api/routes/      # FastAPI route handlers
├── db/              # Database session management
├── models/          # SQLAlchemy (database.py) & Pydantic (schemas.py)
├── services/        # Business logic (VCF parsing, API clients)
├── config.py        # Settings from .env
└── main.py          # FastAPI app entry point

frontend/src/
├── components/      # Reusable UI components
├── pages/           # Page components (route targets)
├── services/        # API client (api.ts)
├── hooks/           # React Query hooks
├── types/           # TypeScript type definitions
├── App.tsx          # Router configuration
└── main.tsx         # React entry point
```

## Key Patterns

1. **Background Tasks** - Use FastAPI BackgroundTasks for long operations:
```python
@router.post("/files/{filename}/parse")
async def parse_vcf(filename: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(_load_variants_task, file_id, filepath)
```

2. **Database Sessions** - Use dependency injection:
```python
async def endpoint(db: Session = Depends(get_db)):
    ...
```

3. **React Query** - Use for all API data fetching with proper keys.

4. **Environment Variables** - Store in `.env`, access via `backend/config.py`.

## Common Issues

- **Import errors**: Always run Python from project root with `PYTHONPATH=.`
- **Database schema changes**: Delete `data/alphagenome.db` and recreate
- **Large files**: Never commit VCF/annotation files (see `.gitignore`). `RAW/` is also gitignored.
- **SQLAlchemy type hints**: LSP errors on Column assignments are expected, ignore them
- **No rsIDs in VCFs**: All variant rsID fields are `.`. Any new annotation matching logic must use position-based lookup (chromosome + position + ref + alt), not rsID. See `variants.py` for the pattern.
- **Symbolic alleles**: CNV/SV VCFs contain `<DEL>`, `<DUP>`, etc. Code that compares ref/alt string lengths must handle these (see `vcf_parser.py:_determine_variant_type()`).
- **ClinVar assembly**: Must load with `GRCh37` to match the VCF data. The default is set in `config.py:genome_assembly` and used by `clinvar_db.py:load_variant_summary()`.
