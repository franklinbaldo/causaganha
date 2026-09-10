---
type: "RunOutcome"
id: "run-outcomes/20260910t033931z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260910T033931Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "partial"
summary: "Fixed src/djen_backup/engine.py's run_pipeline: SyncConfig.upload_only ('Upload already-discovered available entries (backlog drain)', per CLAUDE.md and the upload() subcommand's docstring) only gated Phase 0 IA discovery -- the checker phase (check_queue population + checker_tasks) ran unconditionally, so 'djen-backup upload' still made live DJEN calls for every entry whose availability wasn't already known, mirroring the check_only 'no I/O' bug PR #1397 fixed on the sibling flag. Gated check_queue/checker_tasks on 'not config.upload_only' using the same empty-list-sentinel pattern PR #1397 established. New RED->GREEN regression test tests/djen_backup/test_upload_only_no_djen_check.py; full tests/djen_backup/ suite (119 tests) green; full repo suite (~1918 tests) green except one pre-existing, unrelated sandbox-network failure (test_agent_stdio_recipe.py, predates this change). ruff check/format clean. PR #1403 opened against main and subscribed for activity; work_status=partial because CI/merge confirmation is pending (handoff-pr-1403-awaiting-ci created)."
next_move: "A future round should check PR #1403's CI status and mergeable_state, merge (squash) once green and clean, then archive handoff-pr-1403-awaiting-ci. Separately: this round's fix closes the second of what may be a small class of 'documented CLI-mode I/O contract not actually enforced in run_pipeline' bugs (check_only was the first, in PR #1397; upload_only is the second). The remaining SyncConfig fields worth auditing the same way, not yet checked: skip_if_mostly_complete, publish_live_status, dry_run, fail_fast -- a future round could grep each field's read sites in run_pipeline/service.py against its documented behavior the same way this round and the prior one did for check_only/upload_only."
goals_advanced: ["run-goals/20260910t033931z-do-the-best-useful-work-availab/goal-upload-only-no-djen-check"]
evidence: ["evidence-red-test", "evidence-diff-and-green"]
checks: ["check-full-suite-and-ruff"]
---

# RunOutcome
