"""``djen_backup_status`` tool (RFC 0013 Fase 3A)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from djen_backup import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


class DjenBackupStatusResult(BaseModel):
    """Summary of the local DJEN sync manifest."""

    total: int = Field(description="Total (tribunal, date) entries recorded.")
    uploaded: int = Field(description="Entries already uploaded to Internet Archive.")
    available: int = Field(description="Entries confirmed available on DJEN, pending upload.")
    absent: int = Field(description="Entries confirmed absent on DJEN (no publication).")
    unknown: int = Field(description="Entries not yet checked against DJEN.")


def register(mcp: FastMCP) -> None:
    """Register ``djen_backup_status`` on *mcp*."""

    @mcp.tool(
        name="djen_backup_status",
        annotations={
            "title": "DJEN sync manifest status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def djen_backup_status(
        manifest_file: str = str(service.DEFAULT_MANIFEST_FILE),
    ) -> DjenBackupStatusResult:
        """Summarize the local DJEN sync manifest: coverage across tribunals and dates.

        Reads `sync-manifest.csv` from local disk only — no network call, no
        IA fetch, no credentials involved. The canonical source of truth is
        the `sync-manifest.parquet` on Internet Archive (see
        `docs/planning/manifest-source-of-truth.md`); this tool only sees
        whatever local CSV cache already exists on this machine, which can
        lag behind IA. Never triggers a sync, upload, or reset; for that, use
        the `djen-backup` CLI.

        Args:
            manifest_file: Path to the local manifest CSV. Defaults to
                "data/sync-manifest.csv".

        Returns:
            All-zero counts when the manifest doesn't exist yet or is empty.
        """
        result = service.manifest_status(Path(manifest_file))
        return DjenBackupStatusResult(
            total=result.total,
            uploaded=result.uploaded,
            available=result.available,
            absent=result.absent,
            unknown=result.unknown,
        )
