---
type: "RunOutcome"
id: "run-outcomes/20260914t152436z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260914T152436Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "updated"
work_status: "complete"
summary: "Completed the local diff/verification slice of issue #1471's TJRO 2026 pilot validation: downloaded djen-tjro-2026/comunicacoes.parquet (1,041,723 rows), regenerated it via PR #1473's unified writer, and verified row count, id-set, CNJ normalization contract, other-fields-untouched, footer KV metadata/compression, true physical sort order (file_row_number + lag(), resolving a footer-stats boundary-tie ambiguity that scripts/audit_cnj_parquets.py deliberately leaves unresolved for its own read-only-by-design reasons), and the issue's named spot-check CNJ -- all passed (docs/planning/evidence/pilot-tjro-2026-local-comparison.json). New reusable script scripts/validate_pilot_tjro_2026.py + 4 unit tests, full repo suite/ruff green. Opened PR #1478, posted results to issue #1471, appended a wiki consolidation entry, archived handoffs/handoff-issue-1471-pilot-validation and created handoffs/handoff-issue-1471-perf-and-readback (target session_type: standard-experience) for the remaining DuckDB-perf-measurement and Archive-read-back-proof scope."
next_move: "Follow-up round (ideally Experience-typed per handoffs/handoff-issue-1471-perf-and-readback): confirm PR #1478's CI and merge it, then measure DuckDB native/WASM query latency under the new ordering and do a controlled Archive publish/read-back proof before recording #1471's advance/revise/hold decision. Separately, wiki/continuous-loop-operational-invariants.md is now ~190 lines in one long Evidence & Lineage list -- a future round's judgment call on splitting it remains open per the immediately preceding round's own next_move."
goals_advanced: ["run-goals/20260914t152436z-do-the-best-useful-work-availab/goal-validate-pilot-and-consolidate"]
evidence: ["run-evidence/20260914t152436z-do-the-best-useful-work-availab/evidence-pilot-validation-and-wiki-update"]
checks: ["run-checks/20260914t152436z-do-the-best-useful-work-availab/check-handoff-environment", "run-checks/20260914t152436z-do-the-best-useful-work-availab/check-handoff-disposition", "run-checks/20260914t152436z-do-the-best-useful-work-availab/check-structural-conformance"]
---

# RunOutcome
