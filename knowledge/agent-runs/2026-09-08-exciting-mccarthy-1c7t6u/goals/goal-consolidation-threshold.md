---
type: AgentGoal
id: "2026-09-08-exciting-mccarthy-1c7t6u-goal-consolidation-threshold"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
goal: "Fix web/src/queries/consolidation_status.qmd's hardcoded `tribunals_uploaded >= 90` threshold for classifying a date as 'fully uploaded', deriving it from the manifest's own tribunal count instead of a literal."
rationale: "web/src/queries/consolidation_status.qmd:27-28 classifies a date as 'fully uploaded' with COUNT(DISTINCT tribunal) FILTER (...) >= 90 -- a hardcoded literal compared against src/causaganha/config.py's TRIBUNAIS list, which has 96 entries (confirmed by direct count). Any date where 90-95 of 96 tribunals uploaded (a partial outage, a slow straggler tribunal) is misclassified as fully uploaded, inflating the public consolidation-completeness metric and hiding real backlog. The magic number also silently breaks in any smaller manifest (test fixtures, or any future roster change) since it never reflects how many tribunals the manifest actually tracks. This dataset had zero test coverage and shipped in the same commit as an unrelated circuit-breaker PR, so it was never exercised end to end."
success_signal: "A test that renders the real web/src/queries/consolidation_status.qmd against a manifest fixture with a small, known tribunal universe (3 tribunals) demonstrates the bug RED (a date where all 3 tribunals uploaded is NOT counted in dates_fully_uploaded, because 3 < 90), then goes GREEN after the query is fixed to compare tribunals_uploaded against the manifest's own COUNT(DISTINCT tribunal) instead of a literal. Full Python suite (uv run pytest -q), ruff check, and ruff format --check stay green. okf-parser check stays conformant."
status: "achieved"
---

# Goal: fix consolidation_status.qmd's hardcoded 90-tribunal threshold

Found via um subagente Explore que buscou candidatos frescos com forma TDD (RED/GREEN), já que as filas de issues e PRs desta rodada estavam esgotadas. Verificado de forma independente: `src/causaganha/config.py`'s `TRIBUNAIS` tem 96 entradas, `consolidation_status.qmd` usa o literal `90`. Escolhido entre os três candidatos retornados pelo subagente por ser um bug de correção de métrica ao vivo, testável de forma direta, sem exigir uma decisão arquitetural prévia (ao contrário do candidato `except Exception`/BLE001).
