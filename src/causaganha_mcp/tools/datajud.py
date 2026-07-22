"""``datajud_status`` and ``datajud_facetas`` tools (RFC 0013 Fase 3A/3B)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import httpx
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from datajud import service
from datajud.client import (
    API_KEY_ENV,
    DEFAULT_TRIBUNAL,
    WIKI_ACESSO_URL,
    DataJudAuthError,
    DataJudError,
    DataJudProtocolError,
    DataJudRateLimitError,
)


if TYPE_CHECKING:
    from fastmcp import FastMCP


# Internal MCP call budget for `datajud_facetas` — NOT exposed as a tool
# parameter. `DataJudClient`'s own defaults (timeout=90s, max_retries=5,
# 2/4/8/16/30s backoff) are tuned for the `enrich` CLI's long-running batch
# ingestion, where riding out a DataJud hiccup is worth minutes of waiting.
# An interactive MCP call is a different budget: an unlucky timeout there
# could keep this tool open for ~10 minutes before producing a ToolError
# (RFC 0013 Fase 3B review) — long enough for a host to give up waiting
# before the structured error even arrives. These numbers trade some of
# that ingestion-grade resilience for a call that fails within roughly a
# minute worst case (3 attempts * 20s timeout + ~3s of backoff).
_FACETAS_TIMEOUT = 20.0
_FACETAS_MAX_RETRIES = 2
_FACETAS_BACKOFF_BASE = 1.0


class DatajudStatusResult(BaseModel):
    """Summary of the local DataJud manifest."""

    found: bool = Field(description="False when the manifest doesn't exist or has no entries.")
    total: int = Field(default=0, description="CNJs consulted so far.")
    ok: int = Field(default=0, description="CNJs whose last consult succeeded.")
    com_docs: int = Field(default=0, description="Consulted CNJs with at least one document.")
    sem_docs: int = Field(default=0, description="Consulted CNJs with zero documents found.")
    com_erro: int = Field(default=0, description="CNJs whose last consult failed.")


class DatajudFacetaBucket(BaseModel):
    """One aggregation bucket returned by ``datajud_facetas``."""

    chave: str = Field(description="Facet value (e.g. a classe or assunto name).")
    qtd: int = Field(description="Document count for this value.")


class DatajudFacetasResult(BaseModel):
    """Aggregation of a tribunal's DataJud acervo by one dimension."""

    tribunal: str = Field(description="Tribunal queried, lowercase (e.g. 'tjro').")
    por: str = Field(description="Dimension aggregated by.")
    total: int = Field(
        description="Total documents in the tribunal's acervo — all facet "
        "values, not just the buckets returned below."
    )
    buckets: list[DatajudFacetaBucket] = Field(
        description="Top facet values by document count, largest first."
    )


def _facetas_tool_error(exc: Exception) -> ToolError:
    """Map the DataJud client's error taxonomy to a structured ``ToolError``."""
    if isinstance(exc, DataJudAuthError):
        return ToolError(
            "DataJud rejected the configured API key (HTTP 401). This is an "
            "operator-level credential problem, not something retriable from "
            f"here — fetch a current key at {WIKI_ACESSO_URL} and set the "
            f"{API_KEY_ENV} environment variable."
        )
    if isinstance(exc, DataJudRateLimitError):
        return ToolError(
            "DataJud rate-limited this request past the retry budget. "
            "Recoverable: wait a bit and call datajud_facetas again."
        )
    if isinstance(exc, DataJudProtocolError):
        return ToolError(f"DataJud returned an unparseable response: {exc}")
    if isinstance(exc, httpx.TimeoutException | httpx.TransportError):
        return ToolError(
            "Network error reaching DataJud (timeout or connection failure). "
            "Recoverable: retry datajud_facetas; if it persists, the DataJud "
            "API itself may be down."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        return ToolError(f"DataJud returned HTTP {exc.response.status_code} for this query.")
    return ToolError(f"DataJud query failed: {exc}")


def register(mcp: FastMCP) -> None:
    """Register ``datajud_status`` and ``datajud_facetas`` on *mcp*."""

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

    @mcp.tool(
        name="datajud_facetas",
        annotations={
            "title": "DataJud facet aggregation",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def datajud_facetas(
        tribunal: str = DEFAULT_TRIBUNAL,
        por: Literal["classe", "assunto", "orgao", "grau", "sistema"] = "classe",
        limite: Annotated[
            int, Field(ge=1, le=100, description="Max number of buckets to return.")
        ] = 15,
    ) -> DatajudFacetasResult:
        """Aggregate a tribunal's DataJud acervo by one dimension (classe, assunto, ...).

        Queries the live public DataJud API (network call, unlike
        `datajud_status`) to count documents grouped by *por*, without
        downloading any document. Use this to answer questions like "what
        are the top 10 classes in TJRO's acervo?" without fetching or
        enriching individual processos.

        Args:
            tribunal: Tribunal to query, lowercase (e.g. "tjro"). Defaults to
                the same tribunal the `datajud` CLI defaults to.
            por: Dimension to aggregate by.
            limite: Max buckets to return, 1-100. The `total` field always
                reflects the full acervo, even when `limite` truncates the
                bucket list.

        Returns:
            The full acervo total plus the top `limite` buckets, largest
            first.

        Raises:
            A structured error (via MCP's tool-error channel, not a crash)
            when DataJud rejects the API key, rate-limits past the retry
            budget, returns an unparseable body, or is unreachable. Uses a
            tighter internal timeout/retry budget than the `datajud enrich`
            CLI (roughly a minute worst case, not minutes).
        """
        try:
            total, buckets = await service.facetas(
                tribunal,
                por,
                limite,
                request_timeout=_FACETAS_TIMEOUT,
                max_retries=_FACETAS_MAX_RETRIES,
                backoff_base=_FACETAS_BACKOFF_BASE,
            )
        except (DataJudError, httpx.HTTPError) as exc:
            raise _facetas_tool_error(exc) from exc
        return DatajudFacetasResult(
            tribunal=tribunal,
            por=por,
            total=total,
            buckets=[
                DatajudFacetaBucket(chave=bucket["chave"], qtd=bucket["qtd"]) for bucket in buckets
            ],
        )
