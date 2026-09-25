---
type: "Handoff"
id: "handoffs/handoff-issue-1610-artifact-url-followup"
title: "Terminar issue #1610: validador equivalente no lado TypeScript e auditoria de outros consumidores de indice_processual.parquet"
created_at: "2026-09-25T01:40:39.260800Z"
status: "active"
created_by_run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
state: "PR #1622 fechou a metade Python do #1610 (src/causaganha/processos/service.py::_validate_artifact_url, wired em _fonte_urls, 12 testes GREEN, suite completa verde). Falta: (1) a mesma política (https-only, host archive.org, path /download/*.parquet, sem query/fragment/aspas) no lado TypeScript que consulta a mesma classe de URL de manifesto no navegador (web/src/lib/processoCnj.ts, consumido por web/src/components/DuckDBExplorer.svelte e ProcessoLookup.svelte); (2) auditar se scripts/processo_query_plan_compare.py ou outro consumidor de indice_processual.parquet fora de service.py interpola arquivo_ia_url em SQL sem passar pela mesma validação."
next_action: "Uma vez PR #1622 mergeado: (a) portar _validate_artifact_url para TypeScript com os mesmos casos de teste (host estranho/http/file/query/fragment/aspas/path fora do padrão) cobrindo processoCnj.ts; (b) grep por outros usos de arquivo_ia_url fora de service.py e aplicar a mesma política; (c) fechar issue #1610 apenas depois que ambos os lados (Python e TypeScript) estiverem cobertos, conforme o próprio critério de conclusão da issue."
references: ["https://github.com/franklinbaldo/causaganha/issues/1610", "https://github.com/franklinbaldo/causaganha/pull/1622"]
goals: []
repository_head: "3c0c95a16d2c962e1135da4fa002eae32603a12f"
repository_branch: "claude/exciting-mccarthy-swocg8"
repository_dirty: false
repository_diff_digest: ""
target_session_type: "session-types/standard-experience"
---

# Handoff
