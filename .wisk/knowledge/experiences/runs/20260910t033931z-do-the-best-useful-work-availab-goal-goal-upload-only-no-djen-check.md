---
type: "RunGoal"
id: "run-goals/20260910t033931z-do-the-best-useful-work-availab/goal-upload-only-no-djen-check"
run: "runs/20260910T033931Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Make 'djen-backup upload' genuinely honor its documented contract ('Upload already-discovered available entries (backlog drain)'): when SyncConfig.upload_only is True, run_pipeline must never probe DJEN for entries whose availability is not already known."
rationale: "Reading src/djen_backup/engine.py's run_pipeline (following up on the immediately preceding merged fix for check_only in PR #1397, whose own next_move flagged upload_only as an unverified sibling) showed upload_only only gates Phase 0 IA discovery (engine.py:393, 'if not config.upload_only: existing_items = await _discover_ia_items(manifest)'). The 'unknown entries' priority queue (check_queue) and the checker_tasks pool that drains it by calling _classify_djen_status -> get_caderno_url (a live DJEN HTTP call) are built and started completely unconditionally, regardless of upload_only. Net effect: 'djen-backup upload' -- documented in CLAUDE.md as '# Only upload already-available entries' and in __main__.py's own upload() docstring as 'Upload already-discovered available entries (backlog drain)' -- still probes DJEN live for every manifest entry whose djen_status/djen_raw is not yet terminal, exactly mirroring the check_only bug just fixed but on the opposite CLI mode. Confirmed via grep that no existing test (tests/djen_backup/test_check_only_no_io.py covers only check_only) exercises upload_only's checker-phase behavior."
success_signal: "tests/djen_backup/test_upload_only_no_djen_check.py: seed a manifest with one entry whose availability is NOT yet known (djen_status='', djen_raw='', ia_status='') and run engine.run_pipeline with upload_only=True, monkeypatching engine_module.get_caderno_url to record any call and raise if invoked. Fails RED on unmodified engine.py (DJEN gets probed for the unknown entry); passes GREEN after gating check_queue population and checker_tasks creation on 'not config.upload_only'. Full tests/djen_backup/ suite and the full Python suite stay green; ruff check/format stay clean; upload_only's existing backlog-drain behavior (download/upload of already-available entries) is unaffected."
status: "active"
---

# RunGoal
