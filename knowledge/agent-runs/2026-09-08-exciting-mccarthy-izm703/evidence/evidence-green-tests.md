---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-izm703-evidence-green-tests"
run_id: "2026-09-08-exciting-mccarthy-izm703"
goal_id: "2026-09-08-exciting-mccarthy-izm703-goal-fix-absent-uploaded-double-count"
kind: "test_green"
reference: "uv run pytest tests/test_render_queries.py -k double_count -v; uv run pytest tests/test_render_queries.py -q (after the .qmd fix)"
summary: "After adding 'AND ia_status != uploaded' to the absent filter in totals.qmd, tribunal_coverage.qmd, and court_reliability.qmd: the 3 new tests pass (absent=0, uploaded=1, bucket sums equal total, court_reliability rate=1.0). Full tests/test_render_queries.py file: 34 passed (up from 31 pre-existing + 3 new)."
---

# Evidência: testes GREEN

Após adicionar `AND ia_status != 'uploaded'` ao filtro `absent` das três `.qmd`: os 3 novos testes passam. `tests/test_render_queries.py` completo: 34 testes, todos verdes.
