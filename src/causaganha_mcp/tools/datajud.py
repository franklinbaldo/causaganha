"""``datajud_status`` tool (RFC 0013 Fase 3A)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from datajud import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


class DatajudStatusResult(BaseModel):
    """Summary of the local DataJud manifest."""

    found: bool = Field(description="False when the manifest doesn't exist or has no entries.")
    total: int = Field(default=0, description="CNJs consulted so far.")
    ok: int = Field(default=0, description="CNJs whose last consult succeeded.")
    com_docs: int = Field(default=0, description="Consulted CNJs with at least one document.")
    sem_docs: int = Field(default=0, description="Consulted CNJs with zero documents found.")
    com_erro: int = Field(default=0, description="CNJs whose last consult failed.")


def register(mcp: FastMCP) -> None:
    """Register ``datajud_status`` on *mcp*."""

    @mcp.tool(
        name="datajud_status",
        annotations={
            "title": "DataJud manifest status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def datajud_status(data_dir: str = str(service.DEFAULT_DATA_DIR)) -> DatajudStatusResult:
        """Summarize the local DataJud manifest: how many CNJs are consulted and found.

        Reads `datajud-manifest.csv` under `data_dir` from local disk only —
        no network call, no credentials involved. Use this to check the
        progress of `datajud enrich` runs (e.g. after the daily
        `datajud-enrich.yml` cron) without a shell. This tool never triggers
        a new consult or upload; for that, use the `datajud` CLI's `enrich`
        command.

        Args:
            data_dir: Directory containing the DataJud manifest and parquets.
                Defaults to "data/datajud", the path the scheduled workflow uses.

        Returns:
            found=False (all counts zero) when the manifest doesn't exist yet
            or has no entries — not an error, just an empty pipeline.
        """
        result = service.manifest_status(Path(data_dir))
        if result is None:
            return DatajudStatusResult(found=False)
        return DatajudStatusResult(
            found=True,
            total=result.total,
            ok=result.ok,
            com_docs=result.com_docs,
            sem_docs=result.sem_docs,
            com_erro=result.com_erro,
        )
