---
type: "RunEvidence"
id: "run-evidence/20260914t152436z-do-the-best-useful-work-availab/evidence-pilot-validation-and-wiki-update"
run: "runs/20260914T152436Z-do-the-best-useful-work-available-in-this-reposi"
kind: "consolidation"
reference: "../wiki/continuous-loop-operational-invariants.md"
summary: "Added one bullet to wiki/continuous-loop-operational-invariants.md (169 -> 189 lines) documenting: (1) issue #1471's local pilot validation of djen-tjro-2026 passing every acceptance-criteria item this round covers (docs/planning/evidence/pilot-tjro-2026-local-comparison.json: row_count_matches, id_set_matches, normalization_contract_violations=0, other_fields_untouched, kv_metadata_matches_expected, candidate_sort_violations=0, spot_check_agrees -- all true/0), and (2) the generalizable footer-stats-vs-row-level-check distinction found while building it: scripts/audit_cnj_parquets.py's ranges_overlap deliberately treats a tied row-group boundary as unproven-sorted (correct for its read-only, no-row-data-download constraint), but scripts/validate_pilot_tjro_2026.py already has full row access so it resolves the same ambiguity definitively via DuckDB's file_row_number + a lag() window check instead of inheriting the conservative footer-only answer. New code: scripts/validate_pilot_tjro_2026.py (comparison script, reuses audit_cnj_parquets.ranges_overlap for informational footer context) and tests/test_validate_pilot_tjro_2026.py (4 tests, all green, plus full uv run pytest -q suite confirmed green with no regressions and ruff check/format clean)."
goal: "run-goals/20260914t152436z-do-the-best-useful-work-availab/goal-validate-pilot-and-consolidate"
---

# RunEvidence
