---
created_at: "2026-09-25T01:40:39.260800Z"
created_by_run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
goals: []
id: "handoffs/handoff-issue-1610-artifact-url-followup"
next_action: "Uma vez PR #1622 mergeado: (a) portar _validate_artifact_url para TypeScript com os mesmos casos de teste (host estranho/http/file/query/fragment/aspas/path fora do padrão) cobrindo processoCnj.ts; (b) grep por outros usos de arquivo_ia_url fora de service.py e aplicar a mesma política; (c) fechar issue #1610 apenas depois que ambos os lados (Python e TypeScript) estiverem cobertos, conforme o próprio critério de conclusão da issue."
references: ["https://github.com/franklinbaldo/causaganha/issues/1610", "https://github.com/franklinbaldo/causaganha/pull/1622"]
repository_branch: "claude/exciting-mccarthy-swocg8"
repository_diff_digest: ""
repository_dirty: "false"
repository_head: "3c0c95a16d2c962e1135da4fa002eae32603a12f"
state: "PR #1622 fechou a metade Python do #1610 (src/causaganha/processos/service.py::_validate_artifact_url, wired em _fonte_urls, 12 testes GREEN, suite completa verde). Falta: (1) a mesma política (https-only, host archive.org, path /download/*.parquet, sem query/fragment/aspas) no lado TypeScript que consulta a mesma classe de URL de manifesto no navegador (web/src/lib/processoCnj.ts, consumido por web/src/components/DuckDBExplorer.svelte e ProcessoLookup.svelte); (2) auditar se scripts/processo_query_plan_compare.py ou outro consumidor de indice_processual.parquet fora de service.py interpola arquivo_ia_url em SQL sem passar pela mesma validação."
status: "archived"
target_session_type: "session-types/standard-experience"
title: "Terminar issue #1610: validador equivalente no lado TypeScript e auditoria de outros consumidores de indice_processual.parquet"
type: "Handoff"
continued_by_run: "runs/20260925T042504Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-25T04:26:29.418174Z"
resolution: "resolved: PR #1624 (merged as b22c449) portou a mesma politica de validacao de arquivo_ia_url (https-only, host archive.org, path /download/*.parquet, sem query/fragment/aspas) para o lado TypeScript (web/src/lib/processoCnj.ts::validateArtifactUrl, wired em fonteUrls/buscarProcesso), com 5 testes RED->GREEN e suite web inteira (560 testes) verde. DuckDBExplorer.svelte foi auditado e confirmado que nao consome arquivo_ia_url diretamente. Ambos os lados (Python via PR #1622, TypeScript via PR #1624) agora cobertos -- issue #1610 pode ser fechada."
---

# Handoff
