import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path

import google.generativeai as genai
import structlog


logger = structlog.get_logger()


class EmbeddingCache:
    def __init__(self, db_path: str = ".causaganha/embeddings_cache.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    key TEXT PRIMARY KEY,
                    vector BLOB
                )
            """)

    def _hash_text(self, text: str, model_name: str) -> str:
        return hashlib.sha256(f"{model_name}:{text}".encode()).hexdigest()

    def get(self, text: str, model_name: str) -> list[float] | None:
        key = self._hash_text(text, model_name)
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute("SELECT vector FROM embeddings WHERE key = ?", (key,)).fetchone()
                if row:
                    return json.loads(row[0])
        except Exception:
            # Handle potential db errors gracefully
            pass
        return None

    def set(self, text: str, model_name: str, vector: list[float]):
        key = self._hash_text(text, model_name)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings (key, vector) VALUES (?, ?)",
                    (key, json.dumps(vector)),
                )
        except Exception:
            pass


class GeminiEmbedder:
    def __init__(
        self,
        model_name: str = "models/embedding-001",
        cache: EmbeddingCache | None = None,
    ):
        self.model_name = model_name
        self.cache = cache

        # Configure genai if api_key is available in settings or env
        # Assuming google-generativeai picks up GOOGLE_API_KEY env var automatically
        # but we can try to be explicit if settings has it.
        # Based on config.py it might not be exposed as a property if not defined, so rely on env.

    async def embed(self, text: str) -> list[float] | None:
        if not text:
            return None

        if self.cache:
            cached = self.cache.get(text, self.model_name)
            if cached:
                return cached

        try:
            # Run blocking I/O in thread
            result = await asyncio.to_thread(
                genai.embed_content,
                model=self.model_name,
                content=text,
                task_type="classification",
            )
            embedding = result["embedding"]

            if self.cache:
                self.cache.set(text, self.model_name, embedding)

            return embedding
        except Exception as e:
            logger.error("embedding_failed", error=str(e))
            return None
