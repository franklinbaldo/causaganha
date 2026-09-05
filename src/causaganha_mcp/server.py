"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3, RFC 0014).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect. Product tools are the primary public surface; pipeline
status tools remain available for operator diagnostics without becoming a
prerequisite for normal agent use.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import (
    datajud,
    datajud_processo,
    decisoes,
    djen_backup,
    processo,
    publicacoes,
    status,
    stj_acordaos,
    tjro_juris,
)


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "Escolha a tool pelo trabalho que o usuário quer fazer:\n"
            "- Processo preservado e contexto histórico (ARQUIVO): `processo_consultar`.\n"
            "- Estado processual atual e movimentos oficiais (ESTADO): `processo_estado`.\n"
            "- Localizar publicações preservadas por processo, pessoa, OAB, texto, tribunal ou período: `publicacoes_buscar`.\n"
            "- Teor de decisão, acórdão, ementa ou tese (TEOR): `decisoes_buscar`.\n"
            "Tools de status/facetas são auxiliares para diagnóstico ou agregação. "
            "Use a cobertura, freshness, fonte e limitações retornadas por cada tool para interpretar ausência ou indisponibilidade."
        ),
    )
    datajud.register(mcp)
    datajud_processo.register(mcp)
    tjro_juris.register(mcp)
    stj_acordaos.register(mcp)
    djen_backup.register(mcp)
    status.register(mcp)
    processo.register(mcp)
    publicacoes.register(mcp)
    decisoes.register(mcp)
    return mcp


mcp = build_server()
