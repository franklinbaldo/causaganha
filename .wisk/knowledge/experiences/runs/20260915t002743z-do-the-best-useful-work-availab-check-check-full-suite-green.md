---
type: "RunCheck"
id: "run-checks/20260915t002743z-do-the-best-useful-work-availab/check-full-suite-green"
run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
kind: "test-suite"
procedure: "cd web && npm ci && npx vitest run && npx eslint . ; cd .. && uv run ruff check && uv run ruff format --check && uv run pytest -q"
result: "web: 528/528 vitest tests pass (74 files), 0 eslint errors. Python: ruff check clean, ruff format clean (434 files), full pytest suite exit code 0 (all tests pass, 1 skip)."
status: "pass"
evidence: "run-evidence/20260915t002743z-do-the-best-useful-work-availab/evidence-real-browser-cors-confirmation"
---

# RunCheck
