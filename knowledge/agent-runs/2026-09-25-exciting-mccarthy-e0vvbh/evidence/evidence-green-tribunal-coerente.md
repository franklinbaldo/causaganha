---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-e0vvbh-evidence-green-tribunal-coerente"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
goal_id: "2026-09-25-exciting-mccarthy-e0vvbh-goal-tribunal-coerente-manifesto"
kind: "test_green"
reference: "src/causaganha/processos/service.py (ArtifactProvenanceError, _tribunal_da_url, _validar_tribunal_coerente, _indice_sql, _fonte_urls); web/src/lib/processoCnj.ts (buildIndiceSql)"
summary: "GREEN após implementar: `_indice_sql` passou a selecionar também `tribunal`; `_fonte_urls` agrupa (url -> tribunais declarados) e, além da política de URL já existente, chama `_validar_tribunal_coerente(fonte, tribunal, url)` para cada declaração, descartando com aviso ('...tribunal incoerente no índice...') quando o tribunal embutido no item IA (via `_tribunal_da_url`, regex sobre `djen-{tribunal}-{ano}`/`datajud-{tribunal}`) diverge do que o índice declara; fontes não particionadas por tribunal (juris/stj) ou URLs sem o padrão IA (paths locais de teste) retornam None e não são bloqueadas. `tests/causaganha/processos/test_service.py` completo: 42/42 verde (9 unitários + 1 integração novos, mais os 32 pré-existentes sem regressão). Paridade mantida do lado Web: `buildIndiceSql` também passou a selecionar `tribunal` (não consumido ainda, só paridade de linha com o harness #1107); `web/src/lib/processoQueryPlanParity.test.ts` 4/4 verde; `npx vitest run` (suíte web completa) 75 arquivos/560 testes verde, sem regressão."
---

# Evidência GREEN: coerência de tribunal implementada e testada
