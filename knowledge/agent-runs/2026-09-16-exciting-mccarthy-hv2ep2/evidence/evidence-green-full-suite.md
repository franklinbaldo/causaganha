---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-hv2ep2-evidence-green-full-suite"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
kind: "test_green"
reference: "uv run pytest -q, run after run.md (with completed_at/primary_goal_id/result_summary/next_move filled) + knowledge/backlog/issue-1050.md updates were written"
summary: "Full suite green, exit code 0, 0 failures, 1 skip (pre-existing/unrelated). tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round now passes (run.md exists). tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch8_corpus_growth passes GREEN against the real store (document_count=115 >= 115, ceilings=17 >= 17). tests/segmenter_dataset/test_segmenter_audit_scripts.py's extended allowlist assertion passes. ruff check/format already confirmed clean separately."
---

# Evidência: suíte completa GREEN

```
$ uv run pytest -q
[... 100% ...]
=============================== warnings summary ===============================
tests/causaganha_mcp/test_http_health.py:11
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
[exit code 0]
```

Nenhuma falha, nenhum diff de drift nos artefatos gerados
(`web/src/lib/processoConsultar.gen.ts`,
`src/causaganha_mcp/_generated/domain_models.py`) — não foram
regenerados, conforme a nota do próprio scaffold.
