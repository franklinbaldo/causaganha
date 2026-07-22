"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3, RFC 0014).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect of decorating module-level functions — the same
lesson RFC 0013 Fase 2 drew from ``djen_backup``'s old import-time
``structlog.configure()``/stdio reconfiguration: a process that imports
this module (a test, a supervisor, another tool) should not get side
effects it didn't ask for. Each ``tools/*.py`` module exposes a
``register(mcp)`` function instead of decorating at import time.

RFC 0013 Fase 3A scope: read-only, local, deterministic status tools —
``datajud_status``, ``tjro_juris_status``, ``stj_acordaos_status``,
``djen_backup_status``. None of them touch Internet Archive credentials or
make network calls; each reads whatever manifest already exists on local
disk. Fase 3B adds ``datajud_facetas``: still read-only and credential-free,
but it makes a real call to the public DataJud API — a different error
category (timeout, rate limit, network) from the local/deterministic Fase
3A foundation, hence ``openWorldHint=True`` on that one tool only. Ingestion/
upload operations (the full sync, ``drain``, ``consolidate``, ``enrich``
with upload) stay CLI/CI-only per the RFC — they never become tools.

RFC 0014 M1 adds ``causaganha_status`` (a panorama over the same four local
pipelines, calling their ``service.py`` directly — never the other tools via
the MCP protocol itself) and translates every tool's ``title``/
``description``/output field names to Portuguese, since the product and its
users are Brazilian and this text can be shown directly to a host's user.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import datajud, djen_backup, status, stj_acordaos, tjro_juris


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "Tools somente-leitura sobre os quatro pipelines de ingestão do "
            "CausaGanha (djen-backup, tjro-juris, stj-acordaos, datajud), "
            "mais um panorama agregado (causaganha_status). A maioria lê só "
            "um manifest local — sem chamada de rede, sem credencial, sem "
            "mutação; `datajud_facetas` é a exceção, consultando a API "
            "pública do DataJud ao vivo (ainda somente-leitura, ainda sem "
            "credencial no schema). Para ingestão, upload ou backfill, use a "
            "CLI correspondente (djen-backup, tjro-juris, stj-acordaos, "
            "datajud) ou os workflows agendados — isso não é exposto aqui "
            "por design."
        ),
    )
    datajud.register(mcp)
    tjro_juris.register(mcp)
    stj_acordaos.register(mcp)
    djen_backup.register(mcp)
    status.register(mcp)
    return mcp


mcp = build_server()
