---
type: "RunEvidence"
id: "run-evidence/20260910t002623z-do-the-best-useful-work-availab/evidence-red-green-test"
run: "runs/20260910T002623Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/datajud/test_datajud_models_module_surface.py::test_dead_data14_bound_helper_was_removed"
summary: "RED: failed with 'assert not True -- where True = hasattr(models_module, data14_bound)' against the unmodified src/datajud/models.py. GREEN: passes after deleting data14_bound (and its now-unused _DATE_BR_RE/_DATE_ISO_RE regexes) from the function body and its __all__ entry, plus removing its now-orphaned unit test (test_data14_bound_covers_the_whole_day) and import from tests/datajud/test_datajud_models.py. Full tests/datajud/ suite (75 tests) green."
goal: "run-goals/20260910t002623z-do-the-best-useful-work-availab/goal-remove-dead-data14-bound"
---

# RunEvidence
