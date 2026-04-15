from __future__ import annotations

from typing import TYPE_CHECKING, Self

import anyio
import structlog

from causaganha.pipeline.ia_s3 import (
    create_upload_client,
    get_ia_item_id,
    get_ia_s3_auth,
    upload_to_ia,
)


if TYPE_CHECKING:
    from pathlib import Path

    import httpx

    from causaganha.pipeline.ia_s3 import CircuitBreaker

logger = structlog.get_logger()


class IAS3ParquetUploader:
    """Async wrapper for IA S3-compatible parquet uploads.

    Delegates to the canonical ``upload_to_ia`` backend while preserving
    the exact interface expected by ExportOrchestrator.
    """

    def __init__(self, circuit_breaker: CircuitBreaker | None = None, timeout: int = 300) -> None:
        self._auth = get_ia_s3_auth()
        if not self._auth:
            msg = "No Internet Archive S3 credentials found in environment or config."
            raise ValueError(msg)

        self._cb = circuit_breaker
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazily initialize the shared async upload client."""
        if self._client is None:
            self._client = create_upload_client(self._auth, timeout=self._timeout)
        return self._client

    async def upload_parquet(
        self,
        file_path: Path,
        tribunal: str,
        partition_date: str,
        file_size_mb: float | None = None,
        row_count: int | None = None,
    ) -> str:
        """Upload a daily parquet partition to Internet Archive.

        Returns:
            The public archive.org URL for the item on success.

        Raises:
            ValueError: If the file does not exist.
            OSError: If the upload fails or circuit breaker is open.
        """
        if not await anyio.Path(file_path).exists():
            msg = f"File not found: {file_path}"
            raise ValueError(msg)

        item_id = get_ia_item_id(tribunal, partition_date)
        stem = file_path.stem.split("-")[
            -1
        ]  # e.g. "comunicacoes" from "tjro-2025-01-15-comunicacoes"

        metadata_overrides = {
            "x-archive-meta-title": f"CausaGanha {tribunal} {partition_date} ({stem})",
            "x-archive-meta-date": partition_date,
        }

        desc_parts = [f"CausaGanha data partition for {tribunal} on {partition_date}."]
        if row_count is not None:
            desc_parts.append(f"Row count: {row_count}")
        if file_size_mb is not None:
            desc_parts.append(f"Size: {file_size_mb:.2f} MB")
        metadata_overrides["x-archive-meta-description"] = " ".join(desc_parts)

        client = self._get_client()

        success = await upload_to_ia(
            client,
            item_id,
            file_path,
            partition_date,
            metadata_overrides,
            self._cb,
        )

        if not success:
            msg = f"Upload failed for {file_path}"
            raise OSError(msg)

        return f"https://archive.org/details/{item_id}"

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> Self:
        """Enter context."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit context and clean up client."""
        await self.aclose()
