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
            "CausaGanha é uma infraestrutura cívica de dados judiciais públicos. "
            "Use as tools de produto para responder perguntas do usuário sem exigir "
            "conhecimento dos schemas, arquivos, pipelines ou mecanismos de armazenamento. "
            "Use `publicacoes_buscar` quando a pergunta for localizar publicações preservadas "
            "por processo, OAB, parte, advogado, texto, tribunal ou período; ela pesquisa o "
            "ARQUIVO público do CausaGanha no Internet Archive e não consulta o DJEN live. "
            "Para um CNJ, use `processo_consultar` quando a pergunta for sobre o ARQUIVO "
            "reconciliado (publicações preservadas, decisões/documentos e metadados do snapshot) "
            "e `processo_estado` quando a pergunta for sobre ESTADO atual (movimentos, graus "
            "e último marco no DataJud oficial). Um movimento não revela necessariamente o TEOR "
            "do ato; para saber o que uma decisão diz, procure o documento/decisão no arquivo. "
            "`datajud_facetas` serve para perguntas agregadas sobre o acervo oficial do DataJud; "
            "não use uma faceta para inferir o teor de uma decisão ou o estado de um processo "
            "individual. As tools `*_status` e `causaganha_status` são de diagnóstico operacional: "
            "use-as quando a pergunta for sobre saúde, freshness ou execução dos coletores, não "
            "como etapa obrigatória antes de uma consulta. Ausência de registro em uma fonte não "
            "prova inexistência do processo ou do ato; considere a cobertura e as limitações "
            "retornadas pela tool. Todas as tools MCP são somente-leitura: ingestão, upload e "
            "backfill continuam fora desta interface por design."
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
    return mcp


mcp = build_server()
