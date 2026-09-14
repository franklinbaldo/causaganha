---
type: "RunCheck"
id: "run-checks/20260914t152436z-do-the-best-useful-work-availab/check-handoff-disposition"
run: "runs/20260914T152436Z-do-the-best-useful-work-available-in-this-reposi"
kind: "handoff-disposition"
procedure: "Evaluate handoffs/handoff-issue-1471-pilot-validation's transferred goal (run issue #1471's full pilot validation: local diff + DuckDB native/WASM latency measurement + Archive read-back proof + advance/revise/hold decision) against what a Wiki-synthesis-typed round can responsibly complete in one round."
result: "reframed: the goal is real and directly actionable (PR #1473's writer landed, djen-tjro-2026 is the named concrete candidate), but its full scope spans local diffing, live query-latency measurement, and a real Internet Archive publish/read-back proof -- too much for one round, and the Archive-write step in particular is a bigger, separate commitment than a Wiki-type synthesis round's remit. This round completed the LOCAL slice only: downloaded djen-tjro-2026/comunicacoes.parquet (1,041,723 rows), regenerated it via causaganha.consolidate.exporter.export_table_sync (PR #1473's writer), and verified row count/id-set/CNJ-normalization-contract/other-fields-untouched/footer-KV-metadata/compression/physical-sort-order/spot-check-CNJ -- all passed (docs/planning/evidence/pilot-tjro-2026-local-comparison.json). scripts/validate_pilot_tjro_2026.py + tests/test_validate_pilot_tjro_2026.py are new, reusable for any other tribunal/year pilot. DuckDB-native/WASM latency measurement and the Archive read-back proof are explicitly NOT done and are carried forward in a refined handoff for the next (ideally Experience-typed) round."
status: "pass"
evidence: "run-evidence/20260914t152436z-do-the-best-useful-work-availab/evidence-pilot-validation-and-wiki-update"
goal: "run-goals/20260914t152436z-do-the-best-useful-work-availab/goal-validate-pilot-and-consolidate"
---

# RunCheck
