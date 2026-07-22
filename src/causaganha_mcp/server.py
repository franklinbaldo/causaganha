"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect of decorating module-level functions — the same
lesson RFC 0013 Fase 2 drew from ``djen_backup``'s old import-time
``structlog.configure()``/stdio reconfiguration: a process that imports
this module (a test, a supervisor, another tool) should not get side
effects it didn't ask for. Each ``tools/*.py`` module exposes a
``register(mcp)`` function instead of decorating at import time.

Fase 3A scope: read-only, local, deterministic status tools —
``datajud_status``, ``tjro_juris_status``, ``stj_acordaos_status``,
``djen_backup_status``. None of them touch Internet Archive credentials or
make network calls; each reads whatever manifest already exists on local
disk. Fase 3B adds ``datajud_facetas``: still read-only and credential-free,
but it makes a real call to the public DataJud API — a different error
category (timeout, rate limit, network) from the local/deterministic Fase
3A foundation, hence ``openWorldHint=True`` on that one tool only. Ingestion/
upload operations (the full sync, ``drain``, ``consolidate``, ``enrich``
with upload) stay CLI/CI-only per the RFC — they never become tools.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import datajud, djen_backup, stj_acordaos, tjro_juris


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "Read-only tools over CausaGanha's four ingestion pipelines "
            "(djen-backup, tjro-juris, stj-acordaos, datajud). Most tools "
            "read a local manifest file only — no network call, no "
            "credentials, no mutation; `datajud_facetas` is the one "
            "exception, querying the public DataJud API live (still "
            "read-only, still no credentials in its schema). For ingestion, "
            "upload, or backfill operations, use the corresponding CLI "
            "(djen-backup, tjro-juris, stj-acordaos, datajud) or the "
            "scheduled CI workflows — those are not exposed here by design."
        ),
    )
    datajud.register(mcp)
    tjro_juris.register(mcp)
    stj_acordaos.register(mcp)
    djen_backup.register(mcp)
    return mcp


mcp = build_server()
