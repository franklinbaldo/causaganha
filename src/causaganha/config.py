import os
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


# Base paths calculation
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _BASE_DIR / "data"
_DEFAULT_DB_PATH = str(_DATA_DIR / "causaganha.duckdb")

# ---------------------------------------------------------------------------
# Canonical list of DJEN tribunal codes (96 courts)
#
# These are the exact siglas accepted by the DJEN caderno API.  Every script
# that iterates over tribunals MUST import this list instead of keeping a
# local copy so that fixes propagate everywhere at once.
#
# collect.py also fetches /api/v1/comunicacao/tribunal at runtime and merges
# with this list, so new courts are auto-discovered.  This fallback is used
# when the API is unreachable.
# ---------------------------------------------------------------------------
TRIBUNAIS: list[str] = [
    # Federal councils and systems
    "CJF",
    "PJeCor",
    "SEEU",
    # Federal Regional courts
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
    # Superior courts
    "STF",
    "STJ",
    "TST",
    "TSE",
    "STM",
    "CNJ",
    # State courts
    "TJAC",
    "TJAL",
    "TJAM",
    "TJAP",
    "TJBA",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMG",
    "TJMS",
    "TJMT",
    "TJPA",
    "TJPB",
    "TJPE",
    "TJPI",
    "TJPR",
    "TJRJ",
    "TJRN",
    "TJRO",
    "TJRR",
    "TJRS",
    "TJSC",
    "TJSE",
    "TJSP",
    "TJTO",
    # State military courts
    "TJMMG",
    "TJMRS",
    "TJMSP",
    # Labor courts
    "TRT1",
    "TRT2",
    "TRT3",
    "TRT4",
    "TRT5",
    "TRT6",
    "TRT7",
    "TRT8",
    "TRT9",
    "TRT10",
    "TRT11",
    "TRT12",
    "TRT13",
    "TRT14",
    "TRT15",
    "TRT16",
    "TRT17",
    "TRT18",
    "TRT19",
    "TRT20",
    "TRT21",
    "TRT22",
    "TRT23",
    "TRT24",
    # Electoral courts — DJEN requires hyphenated codes
    "TRE-AC",
    "TRE-AL",
    "TRE-AM",
    "TRE-AP",
    "TRE-BA",
    "TRE-CE",
    "TRE-DF",
    "TRE-ES",
    "TRE-GO",
    "TRE-MA",
    "TRE-MG",
    "TRE-MS",
    "TRE-MT",
    "TRE-PA",
    "TRE-PB",
    "TRE-PE",
    "TRE-PI",
    "TRE-PR",
    "TRE-RJ",
    "TRE-RN",
    "TRE-RO",
    "TRE-RR",
    "TRE-RS",
    "TRE-SC",
    "TRE-SE",
    "TRE-SP",
    "TRE-TO",
]

# DataJud public API key defaults.
#
# The CNJ publishes this API key publicly for DataJud access. Keep the runtime
# override in DATAJUD_API_KEY for rotation without deploys, but retain the
# current public key here as the production default so DataJud keeps working
# when no override is provided. When CNJ rotates the key, update this constant
# and append the old/new values to docs/datajud-api-keys.md.
DATAJUD_PUBLIC_API_KEY_DEFAULT = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

# DJEN URLs: direct is the default for local runs in Brazil; proxy is opt-in.
DJEN_DIRECT_URL = os.environ.get("DJEN_DIRECT_URL", "https://comunicaapi.pje.jus.br")
DJEN_PROXY_URL = os.environ.get("DJEN_PROXY_URL", "https://djen-proxy-mhgmawcn3a-rj.a.run.app")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Core
    BASE_DIR: Path = _BASE_DIR
    DATA_DIR: Path = _DATA_DIR
    DB_PATH: str = _DEFAULT_DB_PATH

    # Cloud / GCP
    GCP_PROJECT: str = "my-project"
    GCP_REGION: str = "us-central1"

    # Scheduler
    TOPIC_INGEST: str = "projects/my-project/topics/ingest"
    LOOKBACK_DAYS: int = 1
    PJE_API_URL: str = "https://comunicaapi.pje.jus.br/api/v1"
    COURTS: list[str] = ["TJRO"]

    # LLM Worker
    TOPIC_LLM: str = "projects/my-project/topics/llm"
    TASKS_QUEUE: str = "llm-retry-queue"
    FUNCTION_URL: str = "https://region-project.cloudfunctions.net/llm_worker"

    # Embedding Provider Configuration
    EMBEDDING_PROVIDER: str = "auto"  # Options: "auto", "google", "jina"
    EMBEDDING_PROVIDER_PRIORITY: list[str] = [
        "jina",
        "google",
    ]  # Priority order for auto-selection
    JINA_API_KEY: str | None = None  # Optional: Jina AI API key for embeddings

    # IA
    IA_ACCESS_KEY: str | None = None
    IA_SECRET_KEY: str | None = None

    # PII
    PII_NAMESPACE_UUID: str = "12345678-1234-5678-1234-567812345678"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    def model_post_init(self, _context: Any, /) -> None:
        """Create data directory on initialization."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()

# Backwards compatibility
DB_PATH = settings.DB_PATH
DATA_DIR = settings.DATA_DIR
BASE_DIR = settings.BASE_DIR
