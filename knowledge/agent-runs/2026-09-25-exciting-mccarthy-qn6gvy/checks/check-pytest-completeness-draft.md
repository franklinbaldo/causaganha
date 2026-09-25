---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-qn6gvy-check-pytest-completeness-draft"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
command: "uv run pytest -q (suite completa do repositório, rodada em background durante o rascunho do relatório)"
result: "failed"
summary: "3 falhas, exatamente as documentadas no próprio scaffold como esperadas enquanto o AgentRun está em rascunho (completed_at/result_summary/next_move vazios): tests/test_check_agent_run_completeness.py, tests/web/test_generate_okf_zod_schemas.py e tests/causaganha_mcp/test_okf_domain_models.py. A saída do check de completude também revelou um defeito real nesta rodada (não coberto pelo aviso do scaffold): os 4 arquivos AgentReading usavam o campo `source` em vez de `reference`/`subject`, os 3 AgentEvidence usavam `description` em vez de `reference`/`summary` (e `kind` com valores fora do enum: 'test-red'/'test-green'/'runtime-observado' em vez de 'test_red'/'test_green'/'runtime'), e o AgentCheck usava `procedure`/`result: ok` em vez de `command`/`result: passed`. Corrigidos nesta rodada antes do commit -- okf-parser check (validação estrutural) não pega isso porque valida a forma Markdown/YAML, não o schema relacional por tipo; scripts/check_agent_run_completeness.py é quem de fato compara contra knowledge/okf.schema.sql campo a campo."
---

# Check: pytest completo (rascunho) -- confirma o gap esperado e pega um defeito real de schema
