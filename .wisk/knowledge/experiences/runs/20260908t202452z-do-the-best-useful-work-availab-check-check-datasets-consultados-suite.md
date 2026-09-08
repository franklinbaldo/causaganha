---
type: "RunCheck"
id: "run-checks/20260908t202452z-do-the-best-useful-work-availab/check-datasets-consultados-suite"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/causaganha/decisoes/ tests/causaganha_mcp/test_decisoes_buscar.py tests/causaganha_mcp/test_decisoes_buscar_periodo.py tests/causaganha/processos -q; uv run ruff check src/causaganha/decisoes/search.py tests/causaganha/decisoes/test_search.py; uv run ruff format --check src/causaganha/decisoes/search.py tests/causaganha/decisoes/test_search.py"
result: "19 tests passed, 0 failed; ruff check: All checks passed; ruff format --check: 2 files already formatted."
status: "pass"
evidence: "run-evidence/20260908t202452z-do-the-best-useful-work-availab/evidence-datasets-consultados-green"
goal: "run-goals/20260908t202452z-do-the-best-useful-work-availab/goal-audit-causaganha-mcp"
---

# RunCheck
