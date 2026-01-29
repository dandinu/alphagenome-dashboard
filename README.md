# AlphaGenome Personal Genome Analysis Dashboard

A web dashboard for analyzing whole genome sequencing data using Google DeepMind's AlphaGenome API, with ClinVar and PharmGKB annotations.

## Features

- **VCF File Loading**: Import and parse VCF files from whole genome sequencing
- **Variant Explorer**: Browse, filter, and search your genetic variants
- **AlphaGenome Analysis**: Deep analysis of variants using DeepMind's genomic AI model
- **Disease Risk Panel**: View pathogenic and likely pathogenic variants from ClinVar
- **Pharmacogenomics**: Drug-gene interaction analysis from PharmGKB
- **Annotation Integration**: ClinVar clinical significance and PharmGKB drug annotations

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

# Optional: Database location (defaults to ./data/alphagenome.db)
DATABASE_URL=sqlite:///./data/alphagenome.db
```

### 3. Place Your VCF Files

Copy your VCF files to the `data/vcf/` directory:

```bash
cp /path/to/your/genome.vcf.gz data/vcf/
```

Supported formats:
- `.vcf`
- `.vcf.gz`

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

## Data Privacy

All data processing happens locally on your machine. VCF data and analysis results are stored in a local SQLite database. The only external API calls are to the AlphaGenome service for variant scoring.

## License

For personal use only. See AlphaGenome terms of service for API usage.

## Acknowledgments

- [Google DeepMind AlphaGenome](https://deepmind.google.com/science/alphagenome/)
- [ClinVar](https://www.ncbi.nlm.nih.gov/clinvar/)
- [PharmGKB](https://www.pharmgkb.org/)
