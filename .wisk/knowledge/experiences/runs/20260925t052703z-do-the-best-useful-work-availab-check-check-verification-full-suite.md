---
type: "RunCheck"
id: "run-checks/20260925t052703z-do-the-best-useful-work-availab/check-verification-full-suite"
run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite, pre-merge and post-merge); uv run ruff check .; uv run ruff format --check .; uv run python scripts/render_queries.py --check"
result: "Pre-merge (branch at commit 841158e, before merging origin/main): uv run pytest -q exited 0, all dots, 1 skip -- full suite green including the 2 new render_queries tests. Post-merge (after merging origin/main's PR #1625 into this branch): uv run ruff check . -> 'All checks passed!'; uv run ruff format --check . -> 458 files already formatted; uv run python scripts/render_queries.py --check -> all 18 .qmd contracts OK. Pushed as PR #1626; CI (10 checks: tests(tjro), lint, web, djen-proxy, archive-cors-proxy, CodeQL/Analyze x4, GitGuardian) triggered and in progress at push time -- see PR #1626 for final CI confirmation on the exact merged head."
status: "pass"
---

# RunCheck
