# AlphaGenome Personal Genome Analysis Dashboard

A web dashboard for analyzing whole genome sequencing data using Google DeepMind's AlphaGenome API, with ClinVar and PharmGKB annotations.

![AlphaGenome Dashboard Screenshot](assets/dashboard_screen.png)

![Variant Analysis Screenshot](assets/variant_analysis_screen.png)

**[User Guide](docs/USER_GUIDE.md)** - How to use each section and interpret the data

## Features

- **VCF File Loading**: Import and parse VCF files from whole genome sequencing (SNP, indel, CNV, SV)
- **Variant Explorer**: Browse, filter, and search millions of variants with pagination
- **AlphaGenome Analysis**: Deep analysis of variants using DeepMind's genomic AI model
- **Disease Risk Panel**: View pathogenic and likely pathogenic variants from ClinVar
- **Pharmacogenomics**: Drug-gene interaction analysis from PharmGKB
- **Position-based Annotation Matching**: ClinVar lookup by chromosome + position + ref + alt (works without rsIDs)
- **CNV/SV Support**: Handles symbolic alleles (`<DEL>`, `<DUP>`, `<INV>`) and breakend notation

## Prerequisites

- Python 3.10+
- Node.js 18+
- AlphaGenome API key (get from [DeepMind](https://deepmind.google.com/science/alphagenome/account/settings))

## Quick Start

### 1. Clone and Setup

```bash
cd alphagenome

# Install all dependencies
npm install
```

### 2. Configure Environment

Create a `.env` file in the root directory (or edit the existing one):

```env
# AlphaGenome API Configuration
ALPHAGENOME_API_KEY=your_api_key_here
ALPHAGENOME_PROJECT_ID=your_project_id_here

# Genome assembly (GRCh37 or GRCh38) — must match your VCF alignment
GENOME_ASSEMBLY=GRCh37

# Optional: Database location (defaults to ./data/alphagenome.db)
DATABASE_URL=sqlite:///./data/alphagenome.db
```

### 3. Place Your VCF Files

Copy your VCF files (with tabix indexes) to the `data/vcf/` directory:

```bash
cp /path/to/your/*.vcf.gz /path/to/your/*.vcf.gz.tbi data/vcf/
```

Supported file types:
- `.vcf` and `.vcf.gz` (gzipped recommended for WGS-scale data)
- SNP, indel, CNV, and SV VCFs (including symbolic alleles like `<DEL>`, `<DUP>`)
- Works with unannotated VCFs (no rsIDs or VEP/SnpEff annotations required)

### 4. Start the Application

```bash
# Start both backend and frontend
npm start
```

Or run them separately:

```bash
# Terminal 1: Start backend
npm run backend

# Terminal 2: Start frontend
npm run frontend
```

The application will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000

## Project Structure

```
alphagenome/
├── backend/                 # Python FastAPI backend
│   ├── api/routes/         # API endpoints
│   ├── db/                 # Database configuration
│   ├── models/             # SQLAlchemy & Pydantic models
│   └── services/           # Business logic
├── frontend/               # React TypeScript frontend
│   └── src/
│       ├── components/     # Reusable UI components
│       ├── hooks/          # React Query hooks
│       ├── pages/          # Page components
│       ├── services/       # API client
│       └── types/          # TypeScript definitions
├── data/
│   ├── vcf/               # Place your VCF files here
│   └── annotations/       # ClinVar & PharmGKB data
├── scripts/               # Setup & download scripts
└── .env                   # Configuration
```

## Backend API Endpoints

### Files
- `GET /api/files` - Discover VCF files in data directory
- `GET /api/files/loaded` - List loaded VCF files
- `POST /api/files/{filename}/parse` - Parse and load a VCF file

### Variants
- `GET /api/variants` - List variants (paginated, filterable)
- `GET /api/variants/{id}` - Get variant details
- `GET /api/variants/stats` - Get variant statistics

### Analysis
- `POST /api/analysis/score` - Score variant with AlphaGenome
- `POST /api/analysis/batch` - Batch score multiple variants
- `GET /api/analysis/{variant_id}` - Get analysis results

### Annotations
- `GET /api/annotations/panels/disease-risk` - Disease risk panel
- `GET /api/annotations/panels/pharmacogenomics` - Pharmacogenomics panel
- `GET /api/annotations/clinvar/rsid/{rsid}` - ClinVar lookup
- `GET /api/annotations/pharmgkb/rsid/{rsid}` - PharmGKB lookup

## Downloading Annotation Data

### ClinVar
```bash
python scripts/download_clinvar.py
```
Then load into the database via API (defaults to GRCh37 assembly to match typical WGS alignments):
```bash
curl -X POST "http://localhost:8000/api/annotations/clinvar/load?assembly=GRCh37"
```

### PharmGKB
```bash
python scripts/download_pharmgkb.py
```

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **SQLite** - Local database
- **cyvcf2/pysam** - VCF parsing
- **AlphaGenome SDK** - DeepMind genomic analysis

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Data fetching
- **Recharts** - Visualizations
- **React Router** - Navigation

## Design Notes

- **Position-based annotation matching**: Most WGS pipelines produce VCFs without rsIDs. ClinVar and variant stats use chromosome + position + ref + alt matching as the primary strategy, with rsID lookup as a fallback when available.
- **GRCh37 default**: The genome assembly is configurable (`GENOME_ASSEMBLY` env var) but defaults to GRCh37, which is still the most common WGS alignment target. ClinVar is filtered to the configured assembly during loading.
- **Background loading**: VCF parsing and ClinVar ingestion run as FastAPI background tasks to avoid blocking the API during multi-million-row loads.
- **Symbolic allele handling**: The VCF parser recognizes `<DEL>`, `<DUP>`, `<DUP:TANDEM>`, `<INS>`, `<INV>`, `<CNV>`, and breakend notation rather than misclassifying them by ref/alt string length comparison.

## Data Privacy

All data processing happens locally on your machine. VCF data and analysis results are stored in a local SQLite database. The only external API calls are to the AlphaGenome service for variant scoring.

## License

For personal use only. See AlphaGenome terms of service for API usage.

## Acknowledgments

- [Google DeepMind AlphaGenome](https://deepmind.google.com/science/alphagenome/)
- [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/)
- [PharmGKB](https://www.pharmgkb.org/)
