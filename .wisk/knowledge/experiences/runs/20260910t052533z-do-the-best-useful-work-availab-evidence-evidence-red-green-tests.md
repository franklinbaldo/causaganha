---
type: "RunEvidence"
id: "run-evidence/20260910t052533z-do-the-best-useful-work-availab/evidence-red-green-tests"
run: "runs/20260910T052533Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/causaganha/analysis/test_llm_analyzer_build_analysis.py"
summary: "RED: test_build_analysis_preserves_precedents failed on unmodified llm_analyzer.py -- assert {} == {'Tema 971 STJ': 'confirmado'} (analysis.precedents came back empty). GREEN: after adding precedents=parsed.get('precedents') or {} to _build_analysis's DecisionAnalysis(...) call (llm_analyzer.py), both tests pass. Full uv run pytest -q suite (all files, no filter) stays green; ruff check and ruff format --check on both changed files pass clean."
goal: "run-goals/20260910t052533z-do-the-best-useful-work-availab/goal-llm-analyzer-precedents"
---

# RunEvidence
