---
type: "RunEvidence"
id: "run-evidence/20260910t102506z-do-the-best-useful-work-availab/evidence-red-green-consolidate-progress"
run: "runs/20260910T102506Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_generate_catalog_progress.py"
summary: "scripts/generate_catalog.py's generate_consolidate_progress() computed progress_pct against a target_end hardcoded to date(2026, 2, 3) -- frozen at write time -- while its sibling generate_collect_progress() correctly uses a live datetime.now(tz=UTC).date(). Since real today (2026-09-10) is >7 months past that frozen date, and generate_omission_stats already takes an explicit end_date parameter for the same kind of live boundary, unique_days from real consolidated dates keeps growing past the frozen window while target_days does not, corrupting the public dashboard's consolidate_progress.progress_pct (published consolidate-progress.json -> fetched by scripts/web/generate-data.py -> rendered on the homepage per web/src/components/__steps__/homepage.steps.ts). RED: tests/test_generate_catalog_progress.py against the unmodified function -- TypeError, only 1 positional arg accepted (2 failed). GREEN after adding an end_date parameter (mirroring generate_omission_stats's own signature) and updating the one caller in main(): 2/2 passed."
goal: "run-goals/20260910t102506z-do-the-best-useful-work-availab/goal-audit-tcu-cli"
---

# RunEvidence
