---
goal: "Fix llm_analyzer._build_analysis to preserve the LLM's extracted precedents dict instead of silently dropping it"
id: "run-goals/20260910t052533z-do-the-best-useful-work-availab/goal-llm-analyzer-precedents"
kind: "task-advance"
rationale: "Both LLM prompts (_SYSTEM_PROMPT, _BATCH_SYSTEM_PROMPT) instruct the model to return a 'precedents' map (precedent citation -> confirmado/distinto/ultrapassado). DecisionAnalysis.precedents (models.py:225) exists to hold it and scripts/build_gold_benchmark.py + scripts/daily_benchmark_update.py both persist analysis.precedents into gold_benchmark's precedents MAP column. But _build_analysis (llm_analyzer.py:311-330) copies every other rich field from the parsed JSON except precedents, so it silently falls back to the Pydantic default {} on every single call from analyze_text and analyze_batch -- the precedents column is permanently empty for all LLM-labeled rows despite the prompt asking for exactly this data."
run: "runs/20260910T052533Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new test (tests/causaganha/analysis/test_llm_analyzer_build_analysis.py) calling _build_analysis with parsed={'precedents': {'Tema 971 STJ': 'confirmado'}, ...} asserts analysis.precedents == {'Tema 971 STJ': 'confirmado'}. Fails RED on unmodified llm_analyzer.py (returns {}), passes GREEN after adding precedents=parsed.get('precedents') or {} to the DecisionAnalysis(...) call. Full pytest suite, ruff check, ruff format --check stay green."
type: "RunGoal"
---

# RunGoal
