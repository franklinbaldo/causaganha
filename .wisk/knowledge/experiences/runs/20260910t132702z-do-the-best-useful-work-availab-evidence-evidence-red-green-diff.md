---
type: "RunEvidence"
id: "run-evidence/20260910t132702z-do-the-best-useful-work-availab/evidence-red-green-diff"
run: "runs/20260910T132702Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_except_exception_policy.py (new test_annotate_with_llm_bulkheads_cite_the_bulkhead_adr) + scripts/annotate_with_llm.py:449,489"
summary: "RED: added test_annotate_with_llm_bulkheads_cite_the_bulkhead_adr to tests/test_except_exception_policy.py, scoped to scripts/annotate_with_llm.py only; ran uv run pytest -q tests/test_except_exception_policy.py, it failed listing both offending lines (449, 489: 'except Exception:' with no docs/adr/0011 citation). GREEN: added the one-line '# per-batch bulkhead, see docs/adr/0011' and '# per-document bulkhead, see docs/adr/0011' comments at both sites; re-ran the same test file, both tests pass. Full suite (uv run pytest -q, 1349+ tests) green, uv run ruff check and uv run ruff format --check clean repo-wide."
goal: "run-goals/20260910t132702z-do-the-best-useful-work-availab/goal-annotate-llm-adr-citation"
---

# RunEvidence
