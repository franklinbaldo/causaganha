---
type: "RunEvidence"
id: "run-evidence/20260914t132556z-do-the-best-useful-work-availab/evidence-red-green-tdd"
run: "runs/20260914T132556Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_audit_cnj_parquets.py"
summary: "RED confirmed first: 'uv run pytest -q tests/test_audit_cnj_parquets.py' failed collection with ModuleNotFoundError: No module named 'scripts.audit_cnj_parquets' before scripts/audit_cnj_parquets.py existed. GREEN after implementing classify_file/ranges_overlap/read_footer_stats/list_djen_items/is_tribunal_year_item: 21/21 tests pass, covering the classifier's full decision table (conformant marker wins outright; overlapping row-group CNJ ranges -> reorder_candidate; a lone row group, a null-bounded range, or non-overlapping-but-uncertified ranges all stay verify_values per the issue's explicit warning that absence of overlap does not prove sortedness; a table with no CNJ column -> not_applicable; a read error -> unavailable even for a not_applicable table) plus two DuckDB-backed synthetic-Parquet fixtures that round-trip read_footer_stats -> classify_file end to end."
goal: "run-goals/20260914t132556z-do-the-best-useful-work-availab/goal-audit-cnj-parquets"
---

# RunEvidence
