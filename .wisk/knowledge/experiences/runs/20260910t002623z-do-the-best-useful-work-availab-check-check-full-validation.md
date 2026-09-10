---
type: "RunCheck"
id: "run-checks/20260910t002623z-do-the-best-useful-work-availab/check-full-validation"
run: "runs/20260910T002623Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest tests/datajud/test_datajud_models_module_surface.py -q (RED before fix) && uv run ruff check && uv run ruff format --check && uv run pytest -q (full suite)"
result: "RED confirmed: AssertionError (hasattr True) against unmodified models.py. After the fix: tests/datajud/ 75/75 passed; ruff check: All checks passed; ruff format --check: 408 files already formatted; full pytest suite: all tests passed (1 pre-existing unrelated skip), zero failures."
status: "pass"
evidence: "run-evidence/20260910t002623z-do-the-best-useful-work-availab/evidence-red-green-test"
goal: "run-goals/20260910t002623z-do-the-best-useful-work-availab/goal-remove-dead-data14-bound"
---

# RunCheck
