"""
AlphaGenome Dashboard - Configuration
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AlphaGenome API
    alphagenome_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./data/alphagenome.db"

    # Data paths
    vcf_data_dir: Path = Path("./data/vcf")
    annotations_dir: Path = Path("./data/annotations")

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Genome assembly (GRCh37 or GRCh38)
    genome_assembly: str = "GRCh37"

    # CORS origins for frontend
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate limiting for AlphaGenome API
    alphagenome_requests_per_minute: int = 60
    alphagenome_batch_size: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def clinvar_dir(self) -> Path:
        return self.annotations_dir / "clinvar"

    @property
    def pharmgkb_dir(self) -> Path:
        return self.annotations_dir / "pharmgkb"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Ensure data directories exist
def ensure_directories():
    """Create necessary data directories if they don't exist."""
    settings = get_settings()
    settings.vcf_data_dir.mkdir(parents=True, exist_ok=True)
    settings.clinvar_dir.mkdir(parents=True, exist_ok=True)
    settings.pharmgkb_dir.mkdir(parents=True, exist_ok=True)
