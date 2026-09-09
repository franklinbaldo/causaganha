---
type: "RunCheck"
id: "run-checks/20260909t102506z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260909T102506Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check . && uv run pytest -q (full repo suite)"
result: "ruff: All checks passed. pytest: 3300+ tests, all green (0 failures), including tests/segmenter_dataset/ at 140/140. No regressions from the mechanical.annotations_are_independent addition or its wiring into release.py's _iaa_gates."
status: "pass"
evidence: "run-evidence/20260909t102506z-do-the-best-useful-work-availab/evidence-independence-red-green"
goal: "run-goals/20260909t102506z-do-the-best-useful-work-availab/goal-audit-segmenter-dataset"
---

# RunCheck
