"""``tjro_juris_status`` tool (RFC 0013 Fase 3A)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from tjro_juris import service


if TYPE_CHECKING:
    from fastmcp import FastMCP


# tjro_juris.service has no DEFAULT_DATA_DIR constant — the CLI takes
# data_dir as a required positional argument. This matches the literal
# argv tjro-sync.yml uses ("tjro-juris crawl data/tjro-juris ...").
_DEFAULT_DATA_DIR = "data/tjro-juris"


class TjroJurisStatusResult(BaseModel):
    """Summary of the local TJRO JURIS manifest."""

    total: int = Field(description="Total (tipo, mes_ano) windows recorded.")
    uploaded: int = Field(description="Windows already uploaded to Internet Archive.")
    pending: int = Field(description="Windows crawled but not yet uploaded.")


def register(mcp: FastMCP) -> None:
    """Register ``tjro_juris_status`` on *mcp*."""

    @mcp.tool(
        name="tjro_juris_status",
        annotations={
            "title": "TJRO JURIS manifest status",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def tjro_juris_status(data_dir: str = _DEFAULT_DATA_DIR) -> TjroJurisStatusResult:
        """Summarize the local TJRO JURIS manifest: crawled windows and upload progress.

        Reads `tjro-juris-manifest.csv` under `data_dir` from local disk
        only — no network call, no credentials involved. Use this to check
        progress of the daily `tjro-sync.yml` backfill (`--desde-ano 1988`)
        without a shell. Never triggers a new crawl or upload; for that, use
        the `tjro-juris` CLI's `crawl`/`upload` commands.

        Args:
            data_dir: Directory containing the manifest and parquets.
                Defaults to "data/tjro-juris", the path the scheduled workflow uses.

        Returns:
            All-zero counts when the manifest doesn't exist yet or is empty —
            not an error, just an empty pipeline.
        """
        result = service.manifest_status(Path(data_dir))
        return TjroJurisStatusResult(
            total=result.total,
            uploaded=result.uploaded,
            pending=result.pending,
        )
