---
type: "RunOutcome"
id: "run-outcomes/20260908t085632z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260908T085632Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Fixed a second instance of the same duplicated-classification-drift pattern this session-family just documented in PR #1315: scripts/backfill_probe.py's local _classify(djen_raw) hardcoded {'404','400'} for the 'absent' bucket instead of importing djen_backup.manifest.ABSENT_CODES, so it never learned about the 'no_publications' sentinel. This diagnostic script's entire purpose is to catch drift between the manifest's recorded status and a live re-probe; every no_publications row was silently miscategorized into its own 'other:no_publications' bucket and falsely reported as DRIFT against the live probe (which classifies the same live 200-Sem-comunicacoes response as 'available', since the live capture there is a bare status code, not body-aware). Fixed with RED (tests/test_backfill_probe_classify.py, 6 cases) -> GREEN: replaced the hardcoded literal with the imported canonical ABSENT_CODES set, which also prevents this exact drift from recurring for any future absent sentinel. Full repo suite, ruff check, and ruff format --check stay green."
next_move: "Both drain_unknowns.py (PR #1315) and backfill_probe.py (this PR) are now fixed; a targeted grep for other local reimplementations of DJEN-raw-status classification across scripts/ and src/ found none remaining (ingest_synthetic_segmenter_corpus.py and run_segmenter_training.py matched the earlier grep only incidentally, on unrelated status_code checks -- not DJEN classification). Treat this specific drift pattern as resolved repo-wide for now. Next round should re-verify the issue/PR queue fresh rather than continuing this same audit a third time; if nothing new surfaces, FRONTEND.md's remaining sections and any other duplicated-logic audit are the next-best fallback leads per this wiki's own guidance."
goals_advanced: ["run-goals/20260908t085632z-do-the-best-useful-work-availab/goal-fix-backfill-probe-classify"]
evidence: ["run-evidence/20260908t085632z-do-the-best-useful-work-availab/evidence-backfill-probe-red", "run-evidence/20260908t085632z-do-the-best-useful-work-availab/evidence-backfill-probe-green"]
checks: ["run-checks/20260908t085632z-do-the-best-useful-work-availab/check-backfill-probe-suite"]
---

# RunOutcome
