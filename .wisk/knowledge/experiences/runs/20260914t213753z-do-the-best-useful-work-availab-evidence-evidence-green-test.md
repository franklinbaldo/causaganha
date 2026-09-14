---
type: "RunEvidence"
id: "run-evidence/20260914t213753z-do-the-best-useful-work-availab/evidence-green-test"
run: "runs/20260914T213753Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_audit_cnj_parquets.py + scripts/audit_cnj_parquets.py (post-fix)"
summary: "GREEN: 'uv run pytest -q tests/test_audit_cnj_parquets.py' -> 25 passed (21 pre-existing + 4 new). Implementation: added NATIONAL_INDEX classification constant and NATIONAL_INDEX_ITEM_ID/NATIONAL_INDEX_TABLE constants (causaganha-dashboard/indice_processual) to scripts/audit_cnj_parquets.py; classify_file now short-circuits to NATIONAL_INDEX for that table name (after the read_error check, before the CNJ_TABLES/not_applicable check, preserving the existing 'unavailable overrides everything' invariant); added list_national_index_file() that probes the dashboard item's file list and returns None when not yet published (absent is not unavailable); wired it into audit_catalog() so every report run now includes the national index as its own explicit entry. ruff check and ruff format --check both clean on both files."
goal: "goal-national-index-audit"
---

# RunEvidence
