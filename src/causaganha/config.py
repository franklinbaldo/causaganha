from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


# Base paths calculation
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _BASE_DIR / "data"
_DEFAULT_DB_PATH = str(_DATA_DIR / "causaganha.duckdb")


class Settings(BaseSettings):
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
    EMBEDDING_PROVIDER: str = "auto"  # Options: "auto", "google", "jina", "local"
    EMBEDDING_PROVIDER_PRIORITY: list[str] = [
        "local",  # Try local first (no API costs, privacy)
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

    def model_post_init(self, __context: Any) -> None:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()

# Backwards compatibility
DB_PATH = settings.DB_PATH
DATA_DIR = settings.DATA_DIR
BASE_DIR = settings.BASE_DIR
