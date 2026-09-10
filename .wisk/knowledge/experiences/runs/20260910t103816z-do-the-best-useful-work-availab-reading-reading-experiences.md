---
type: "RunReading"
id: "run-readings/20260910t103816z-do-the-best-useful-work-availab/reading-experiences"
run: "runs/20260910T103816Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "run-outcomes/20260910t102506z-do-the-best-useful-work-availab/outcome-final"
reference: "../experiences/runs/20260910t102506z-do-the-best-useful-work-availab-outcome-outcome-final.md"
finding: "The Experience round this session ran earlier (runs/20260910T102506Z) swept src/tcu_acordaos and src/causaganha_cli clean (both already carefully tested, no live defect), then broadened into the scripts/*.py long tail and found generate_catalog.py's generate_consolidate_progress() computing the public dashboard's progress_pct against a target_end hardcoded to date(2026, 2, 3), frozen relative to its live-'now' sibling generate_collect_progress(). Fixed RED->GREEN via tests/test_generate_catalog_progress.py, landed as PR #1417, handoff handoffs/handoff-pr-1417-awaiting-ci left for this continuation."
---

# RunReading
