---
goal: "Close issue #1470's unaddressed acceptance criterion: classify indice_processual.parquet (the national cross-source index) as its own bucket in scripts/audit_cnj_parquets.py, instead of silently never auditing it, and re-run the audit against the live IA catalog to produce fresh, reproducible evidence."
id: "run-goals/20260914t213753z-do-the-best-useful-work-availab/goal-national-index-audit"
kind: "task-advance"
rationale: "The prior handoff's publish/read-back step for #1471/#1472 stays blocked by missing IA write credentials, same as the last two rounds. Issue #1470's own checklist item 'Classificar o indice nacional separadamente' is unaddressed by the current script (it only enumerates identifier:djen-* items, which never matches the causaganha-dashboard item that hosts indice_processual.parquet) -- a real, scoped, credential-free gap fixable with TDD in this environment."
run: "runs/20260914T213753Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/test_audit_cnj_parquets.py has new RED tests that turn GREEN after the fix (classify_file returns a distinct NATIONAL_INDEX for indice_processual regardless of marker/ranges; list_national_index_file finds/misses the file correctly), ruff check/format clean, and a fresh scripts/audit_cnj_parquets.py run against live archive.org produces a report where causaganha-dashboard/indice_processual is present and classified national_index."
type: "RunGoal"
---

# RunGoal
