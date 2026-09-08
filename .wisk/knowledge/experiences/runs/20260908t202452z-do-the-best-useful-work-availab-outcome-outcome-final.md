---
type: "RunOutcome"
id: "run-outcomes/20260908t202452z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Widened this round's audit sweep past src/causaganha_mcp (clean) into src/datajud, src/causaganha/decisoes, src/causaganha/processos. Both areas were substantially clean, but the decisoes/search.py sweep found a real, untested, user-visible reporting bug: search_decisions returned datasets_consultados=plan.total_datasets even when the STJ branch is skipped (continue) because a cnj or orgao filter makes an STJ match structurally impossible (#1045/#1064) -- so the MCP tool decisoes_buscar reported an inflated dataset count for a source its own limitacoes field said was excluded. Fixed with RED (assert datasets_consultados==1 added to both existing skip-tests, failed at 2==1) -> GREEN (accumulate datasets_consultados from datasets actually iterated inside the loop, after the stj-skip continue) TDD; full causaganha/decisoes + causaganha/processos + causaganha_mcp decisoes_buscar* suites (19 tests) plus ruff check/format all green."
next_move: "Opening a PR for this fix now. This round deliberately deferred one lower-priority finding from the same audit: src/datajud/models.py's data14_bound helper is dead code (zero callers anywhere in the repo, only exercised by its own unit test) -- harmless today but worth removing or wiring into a real date-range-filtered DataJud query in a future round. The next round should also re-verify the issue/PR queue fresh (17 issues remain environment-blocked: segmenter ML training, TCU/TSE data-publishing) before deciding whether to act on data14_bound or sweep a new area."
goals_advanced: ["run-goals/20260908t202452z-do-the-best-useful-work-availab/goal-audit-causaganha-mcp"]
evidence: ["run-evidence/20260908t202452z-do-the-best-useful-work-availab/evidence-datasets-consultados-green"]
checks: ["run-checks/20260908t202452z-do-the-best-useful-work-availab/check-datasets-consultados-suite"]
---

# RunOutcome
