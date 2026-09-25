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
continued_by_run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-25T05:38:27.539650Z"
resolution: "Superseding an earlier archive of this same handoff (continued_by_run runs/20260925T042504Z, archived_at 2026-09-25T04:26:29Z) that closed items (a)/TypeScript-port and the DuckDBExplorer.svelte check via PR #1624, but did not complete item (b)'s full audit -- it never found scripts/render_queries.py. This run finished item (b): scripts/render_queries.py::_register_comunicacoes was interpolating indice_processual.parquet's arquivo_ia_url unvalidated into read_parquet([...]) SQL -- same vulnerability class, now fixed by importing causaganha.processos.service._validate_artifact_url (same pattern as this file's existing tjro_juris.service._PARQUET_SCHEMA import) and dropping invalid URLs with a warning; TDD RED (duckdb.ParserException from a quote-injection fixture) then GREEN, 56/56 tests in test_render_queries.py. src/causaganha/decisoes/published.py::resolve_juris_urls_for_cnj also reads arquivo_ia_url from the index but only uses it for Python set membership filtering against an independently-trusted dataset list, never SQL interpolation -- not the same threat class, no fix needed. scripts/reconcile_processos.py computes arquivo_ia_url as an output column from its own freshly-discovered IA URLs (the trust origin, not a downstream consumer) -- also not in scope. Issue #1610's own completion criteria (both Python and TypeScript sides covered, plus this full audit) are now fully met."
---

# Handoff
