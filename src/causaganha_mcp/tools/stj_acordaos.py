"""``stj_acordaos_status`` tool (RFC 0013 Fase 3A)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from stj_acordaos import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


class StjAcordaosStatusResult(BaseModel):
    """Summary of the local STJ acórdãos manifest."""

    count: int = Field(description="Total files (ZIPs, monthly JSONs, parquet) recorded.")
    uploaded: int = Field(description="Files already uploaded to Internet Archive.")
    pending: int = Field(description="Files downloaded/built but not yet uploaded.")


def register(mcp: FastMCP) -> None:
    """Register ``stj_acordaos_status`` on *mcp*."""

    @mcp.tool(
        name="stj_acordaos_status",
        annotations={
            "title": "STJ acórdãos manifest status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def stj_acordaos_status(
        manifest_path: str = str(service.DEFAULT_MANIFEST),
    ) -> StjAcordaosStatusResult:
        """Summarize the local STJ acórdãos manifest: files tracked and upload progress.

        Reads the manifest CSV from local disk only — no network call, no
        credentials involved. Per-file details (filename, tipo, status) are
        intentionally omitted from this summary to keep the response small;
        use the `stj-acordaos` CLI's `status` command for the full listing.
        Never triggers a new download or upload; for that, use the
        `stj-acordaos` CLI's `download`/`upload` commands.

        Args:
            manifest_path: Path to `stj-manifest.csv`. Defaults to
                "data/stj/stj-manifest.csv", the path the scheduled workflow uses.

        Returns:
            All-zero counts when the manifest doesn't exist yet or is empty —
            not an error, just an empty pipeline.
        """
        result = service.manifest_summary(Path(manifest_path))
        return StjAcordaosStatusResult(
            count=result.count,
            uploaded=result.uploaded,
            pending=result.pending,
        )
