---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-1c7t6u-decision-dynamic-tribunal-count"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
goal_id: "2026-09-08-exciting-mccarthy-1c7t6u-goal-consolidation-threshold"
question: "Should the 'fully uploaded' threshold in consolidation_status.qmd be a corrected literal (96, matching TRIBUNAIS's current length) or derived dynamically from the manifest itself?"
choice: "Derive it dynamically in SQL as (SELECT COUNT(DISTINCT tribunal) FROM manifest), compared against per-date tribunals_uploaded. Also removed the uploaded_dates CTE, which was defined but never referenced by the final SELECT."
rationale: ".qmd query contracts only ever see the manifest (per web/src/queries/README.md and CLAUDE.md's 'Manifest query contracts' section) -- the Python backend doesn't pass config into these; DuckDB only has the registered views. A literal 96 would still silently drift the next time the roster changes, and it would still be wrong for any manifest that legitimately tracks fewer tribunals (a test fixture, or the manifest's own early history before all 96 were onboarded) -- those periods have a real, achievable 100% coverage that a fixed roster-size literal can never register. Deriving the total from the manifest's own COUNT(DISTINCT tribunal) makes 'fully uploaded' mean what it should mean for any manifest slice, self-adjusts if the roster changes, and needs no cross-reference to config.py's Python module in a SQL-only artifact. The unused uploaded_dates CTE was dead SQL bundled in the same original commit, harmless but noisy, and would have been a distraction when reading this query later."
---

# Decisao: derivar o total de tribunais do manifesto, não de `config.py`

Ver `run.md`/`goals/goal-consolidation-threshold.md` para o contexto do bug corrigido.
