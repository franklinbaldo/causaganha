---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-9t0p2a-evidence-green-untrusted-evidence-marker"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
kind: "test_green"
reference: "src/causaganha_mcp/evidence.py, src/causaganha_mcp/tools/publicacoes.py, src/causaganha_mcp/tools/decisoes.py, tests/causaganha_mcp/test_untrusted_evidence_marker.py"
summary: "Implementado src/causaganha_mcp/evidence.py com a constante Literal UNTRUSTED_LEGAL_TEXT='untrusted_legal_text' e adicionado o campo tipo_conteudo (mesmo Literal, com default e docstring explicando a fronteira host/agente) a PublicacaoResult (publicacoes.py) e DecisaoResult (decisoes.py). Docstrings das duas tools (publicacoes_buscar, decisoes_buscar) e docs/MCP_AGENT_EXPERIENCE.md (nova secao 'Evidencia nao e instrucao (#1616)' em Contrato de saida) atualizados para documentar o marcador. uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py: 5/5 verde -- (1)/(2) trecho com frase de prompt injection chega verbatim ao chamador em ambas as tools e tipo_conteudo==untrusted_legal_text; (3) marcador presente mesmo quando trecho=None; (4) JSON schema publicado de cada tool ($defs.PublicacaoResult/$defs.DecisaoResult) declara tipo_conteudo como const='untrusted_legal_text', nao metadado invisivel. Suite completa de tests/causaganha_mcp/ (36 arquivos) permanece 100% verde -- o marcador foi colocado dentro dos modelos de item aninhados (resultados[].tipo_conteudo), nao no envelope de nivel superior, entao _EXPECTED_OUTPUT_FIELDS em test_tool_schema.py (que so verifica as chaves de nivel superior de cada tool) nao precisou de nenhuma atualizacao."
---

# Evidencia: GREEN apos implementar o marcador de evidencia nao-confiavel (#1616)

```
$ uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py
.....                                                                    [100%]
5 passed in 2.35s

$ uv run pytest -q tests/causaganha_mcp/
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 92%]
.................                                                        [100%]
```

O design deliberado de colocar o marcador no modelo de item (`PublicacaoResult`/
`DecisaoResult`), nao no envelope de resultado (`PublicacoesBuscarResult`/
`DecisoesBuscarResult`), evitou tocar o contrato de campos de nivel superior
ja fixado em `tests/causaganha_mcp/test_tool_schema.py::_EXPECTED_OUTPUT_FIELDS`
-- o marcador descreve a confianca do *texto de cada item*, nao do envelope.
