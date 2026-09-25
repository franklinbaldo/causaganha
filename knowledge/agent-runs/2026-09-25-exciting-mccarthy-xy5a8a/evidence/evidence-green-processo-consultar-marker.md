---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-xy5a8a-evidence-green-processo-consultar-marker"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal_id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
kind: "test_green"
reference: "src/causaganha_mcp/tools/processo.py"
summary: "Adicionado tipo_conteudo: Literal['untrusted_legal_text'] = Field(default=UNTRUSTED_LEGAL_TEXT, ...) a DocumentoResult (rotula resumo) e a StjAcordaoResult (rotula tese/ementa), importando a mesma constante causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT ja usada por publicacoes.py/decisoes.py. `uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py`: 9/9 verde (5 pre-existentes + 4 novos). `uv run pytest -q tests/causaganha_mcp/`: suite MCP completa verde, sem regressao. `uv run ruff check`/`format --check` sobre os arquivos tocados: limpo."
---

# Evidência GREEN: marcador presente e testado em processo_consultar

Confirma que, após a mudança, `resumo`/`tese`/`ementa` continuam
passando verbatim (inclusive texto de injeção de prompt) enquanto o item
carrega `tipo_conteudo="untrusted_legal_text"`, tanto no objeto retornado
em runtime quanto no `output_schema` publicado pela tool — sem
regressão na suíte MCP completa.
