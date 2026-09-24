---
type: "RunEvidence"
id: "run-evidence/20260924t202639z-do-the-best-useful-work-availab/evidence-verification-full-suite"
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
kind: "ci"
reference: "uv run ruff check . ; uv run ruff format --check . ; uv run pytest -q (all run locally, exit 0 each)"
summary: "ruff check: all checks passed. ruff format --check: 457 files already formatted (no diffs). pytest -q: full suite green, exit 0, no failures/errors (one pre-existing skip unrelated to this change)."
goal: "run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"
---

# RunEvidence
