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
The aggregate catalog is now sourced from the typed OKF ``Pipeline`` relation;
only the direct Python execution bindings remain in code.

RFC 0014 M2 adds ``processo_consultar`` — the first tool that serves the
end user directly, not the pipeline operator. It reads the canonical
cross-source parquets published to Internet Archive (``causaganha_mcp.tools
.processo`` → ``causaganha.processos.service``), the same artifacts the web
dashboard's ``/processo`` page reads — not a local manifest, and not a
second, independently-published copy of the data. Like ``datajud_facetas``,
it is a real network call (``openWorldHint=True``).
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import (
    datajud,
    djen_backup,
    processo,
    status_catalog,
    stj_acordaos,
    tjro_juris,
)


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "Tools sobre os quatro pipelines de ingestão do CausaGanha "
            "(djen-backup, tjro-juris, stj-acordaos, datajud), um panorama "
            "agregado (causaganha_status), e uma tool de produto para "
            "consultar processos (processo_consultar). A maioria das tools "
            "de pipeline lê só um manifest local — sem chamada de rede, sem "
            "credencial, sem mutação. `datajud_facetas` e "
            "`processo_consultar` são as exceções: consultam dados ao vivo "
            "(API pública do DataJud e os parquets canônicos do Internet "
            "Archive, respectivamente) — ainda somente-leitura, ainda sem "
            "credencial no schema. Para ingestão, upload ou backfill, use a "
            "CLI correspondente (djen-backup, tjro-juris, stj-acordaos, "
            "datajud) ou os workflows agendados — isso não é exposto aqui "
            "por design."
        ),
    )
    datajud.register(mcp)
    tjro_juris.register(mcp)
    stj_acordaos.register(mcp)
    djen_backup.register(mcp)
    status_catalog.register(mcp)
    processo.register(mcp)
    return mcp


mcp = build_server()
