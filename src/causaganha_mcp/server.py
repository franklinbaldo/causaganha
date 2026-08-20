"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3, RFC 0014).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect. Pipeline status tools keep their direct Python service
boundary; the aggregate ``causaganha_status`` now reads stable product metadata
from the typed OKF ``Pipeline`` relation before dispatching those same loaders.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import datajud, djen_backup, processo, status, stj_acordaos, tjro_juris


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
    status.register(mcp)
    processo.register(mcp)
    return mcp


mcp = build_server()
