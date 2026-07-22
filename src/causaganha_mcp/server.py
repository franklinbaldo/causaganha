"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect of decorating module-level functions — the same
lesson RFC 0013 Fase 2 drew from ``djen_backup``'s old import-time
``structlog.configure()``/stdio reconfiguration: a process that imports
this module (a test, a supervisor, another tool) should not get side
effects it didn't ask for. Each ``tools/*.py`` module exposes a
``register(mcp)`` function instead of decorating at import time.

Fase 3A scope: read-only, local, deterministic status tools only —
``datajud_status``, ``tjro_juris_status``, ``stj_acordaos_status``,
``djen_backup_status``. None of them touch Internet Archive credentials or
make network calls; each reads whatever manifest already exists on local
disk. Ingestion/upload operations (the full sync, ``drain``, ``consolidate``,
``enrich`` with upload) stay CLI/CI-only per the RFC — they never become
tools.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import datajud, djen_backup, stj_acordaos, tjro_juris


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "Read-only status tools over CausaGanha's four ingestion pipelines "
            "(djen-backup, tjro-juris, stj-acordaos, datajud). Each tool reads "
            "a local manifest file — no network calls, no credentials, no "
            "mutation. For ingestion, upload, or backfill operations, use the "
            "corresponding CLI (djen-backup, tjro-juris, stj-acordaos, "
            "datajud) or the scheduled CI workflows — those are not exposed "
            "here by design."
        ),
    )
    datajud.register(mcp)
    tjro_juris.register(mcp)
    stj_acordaos.register(mcp)
    djen_backup.register(mcp)
    return mcp


mcp = build_server()
