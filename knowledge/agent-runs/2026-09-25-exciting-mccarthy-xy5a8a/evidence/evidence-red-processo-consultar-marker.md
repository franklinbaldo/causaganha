---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-xy5a8a-evidence-red-processo-consultar-marker"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal_id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
kind: "test_red"
reference: "tests/causaganha_mcp/test_untrusted_evidence_marker.py"
summary: "4 testes novos escritos primeiro contra a API alvo (tipo_conteudo em DocumentoResult/StjAcordaoResult, ainda inexistente): 2 testes de comportamento (resumo/tese/ementa) e 2 parametrizados de schema. `uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py` antes da mudanca de producao: os 2 primeiros falham com AttributeError ('DocumentoResult'/'StjAcordaoResult' object has no attribute 'tipo_conteudo'); os 2 parametrizados falham com KeyError('tipo_conteudo') ao inspecionar tool.output_schema['$defs']. Os 5 testes pre-existentes (publicacoes_buscar/decisoes_buscar) continuam verdes, confirmando que o RED e isolado ao novo comportamento."
---

# Evidência RED: marcador ausente em processo_consultar

Confirma que, antes da mudança de produção, `processo_consultar` não
declara `tipo_conteudo` em `DocumentoResult` nem em `StjAcordaoResult` —
nem no objeto retornado em runtime, nem no schema publicado da tool.
