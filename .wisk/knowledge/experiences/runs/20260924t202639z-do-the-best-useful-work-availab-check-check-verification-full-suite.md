---
type: "RunCheck"
id: "run-checks/20260924t202639z-do-the-best-useful-work-availab/check-verification-full-suite"
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check . && uv run ruff format --check . && uv run pytest -q"
result: "All three commands exited 0: lint clean, formatting clean, full test suite green including the new RED->GREEN tests for issue #1615's tribunal allowlist. The claimed execution (evidence-execution-tribunal-allowlist) is supported by real, reproducible verification, not self-report."
status: "pass"
evidence: "evidence-verification-full-suite"
goal: "run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"
---

# RunCheck
