---
goal: "Audit previously-unswept src/tcu_acordaos and src/causaganha_cli for a real defect in the same lineage as the prior 24 patterns recorded in wiki/continuous-loop-operational-invariants.md, then fix it via RED->GREEN TDD and open a PR."
id: "run-goals/20260910t102506z-do-the-best-useful-work-availab/goal-audit-tcu-cli"
kind: "task-advance"
rationale: "Prior rounds have swept djen_backup, causaganha_mcp, datajud/decisoes/processos, consolidate, segmenter_dataset, .qmd contracts, web/src/lib, web/src/pages, deployment/relay function, tjro_juris, stj_acordaos, tse_processual, and much of scripts/*.py clean; tcu_acordaos and causaganha_cli were only touched incidentally by a broader sweep that found its bug elsewhere (llm_analyzer.py, PR #1408), never read end-to-end for their own invariants."
run: "runs/20260910T102506Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A failing (RED) test reproduces a genuine behavioral defect in one of these modules, a minimal fix turns it GREEN, full validation (ruff + pytest, or npm equivalent) passes, and a PR is opened."
type: "RunGoal"
---

# RunGoal
