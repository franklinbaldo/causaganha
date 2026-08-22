"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3, RFC 0014).

Tool registration happens explicitly inside ``build_server()``, not as an
import-time side effect. Product tools are the primary public surface; pipeline
status tools remain available for operator diagnostics without becoming a
prerequisite for normal agent use.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.tools import datajud, djen_backup, processo, status, stj_acordaos, tjro_juris


def build_server() -> FastMCP:
    """Construct a fresh ``causaganha_mcp`` server with all tools registered."""
    mcp = FastMCP(
        name="causaganha_mcp",
        instructions=(
            "CausaGanha é uma infraestrutura cívica de dados judiciais públicos. "
            "Use as tools de produto para responder perguntas do usuário sem exigir "
            "conhecimento dos schemas, arquivos, pipelines ou mecanismos de armazenamento. "
            "Para um CNJ, prefira `processo_consultar`: ela monta um snapshot reconciliado "
            "com provenance entre as fontes disponíveis. Trate esse resultado como ARQUIVO "
            "(o que o CausaGanha preservou), não como estado processual ao vivo. "
            "`datajud_facetas` serve para perguntas agregadas sobre o acervo oficial do "
            "DataJud; não use uma faceta para inferir o teor de uma decisão ou o estado de "
            "um processo individual. As tools `*_status` e `causaganha_status` são de "
            "diagnóstico operacional: use-as quando a pergunta for sobre saúde, freshness "
            "ou execução dos coletores, não como etapa obrigatória antes de uma consulta. "
            "Preserve sempre a distinção entre ARQUIVO (publicado/preservado), ESTADO "
            "(movimentos e marco processual mais recente) e TEOR (conteúdo de decisões e "
            "documentos). Ausência de registro em uma fonte não prova inexistência do "
            "processo ou do ato; considere a cobertura e as limitações retornadas pela tool. "
            "Todas as tools MCP são somente-leitura: ingestão, upload e backfill continuam "
            "fora desta interface por design."
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
