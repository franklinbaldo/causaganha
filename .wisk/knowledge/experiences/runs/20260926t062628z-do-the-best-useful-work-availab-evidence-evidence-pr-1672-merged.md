---
type: "RunEvidence"
id: "run-evidence/20260926t062628z-do-the-best-useful-work-availab/evidence-pr-1672-merged"
run: "runs/20260926T062628Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "https://github.com/franklinbaldo/causaganha/pull/1672 (squash commit c8119ff435af94c0947f36a39f0ad4fa90cda709 on main)"
summary: "PR #1672 (this round's own docs/knowledge close-out) hit one real regression on its first CI run: tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round failed because this round's own edit to knowledge/backlog/issue-1051.md used last_verified_run_id='runs/20260926T062628Z-...' without the required 'wisk:' provenance prefix the test enforces (confirmed via mcp__github__get_job_logs on the failing check_run, head sha a1f2edb) -- fixed by matching the format already used in issue-1022.md/issue-985.md ('wisk:runs/<timestamp>-...'), verified locally (7/7 tests/knowledge/test_backlog.py passed, ruff clean, okf-parser conformant) before pushing commit 05e72ec. All 14 CI checks then passed on the fixed head, mergeable_state=clean, zero unresolved review threads (only an informational Codex security-review comment with no findings) -- merged via mcp__github__merge_pull_request (squash). mcp__github__list_commits confirms c8119ff landed as new HEAD on main."
goal: "run-goals/20260926t062628z-do-the-best-useful-work-availab/goal-shepherd-pr-1670"
---

# RunEvidence
