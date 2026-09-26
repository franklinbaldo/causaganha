---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-qs1nzy-check-ruff-and-new-tests"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal_id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-formalize-candidate-selection"
command: "uv run ruff check scripts/segmenter_adjudication_candidates.py tests/segmenter_dataset/test_segmenter_adjudication_candidates.py ; uv run ruff format --check <same> ; uv run pytest -q tests/segmenter_dataset/test_segmenter_adjudication_candidates.py"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-qs1nzy-evidence-candidates-script-tests"
summary: "ruff check/format clean on both new files. All 5 new tests pass, including the live-store cross-check against scripts/segmenter_governance_status.py."
---

# Check: ruff + new tests

```
$ uv run ruff check scripts/segmenter_adjudication_candidates.py tests/segmenter_dataset/test_segmenter_adjudication_candidates.py
All checks passed!

$ uv run ruff format --check scripts/segmenter_adjudication_candidates.py tests/segmenter_dataset/test_segmenter_adjudication_candidates.py
2 files already formatted

$ uv run pytest -q tests/segmenter_dataset/test_segmenter_adjudication_candidates.py
.....                                                                    [100%]
5 passed
```

Two of the five tests hit `data/segmenter`'s dedup near-duplicate scan
(~75s each, per `segmenter_dataset.dedup`'s own documented cost at
corpus scale) -- consistent with the existing 18
`test_real_store_reflects_*` tests in
`tests/segmenter_dataset/test_segmenter_governance_status.py`, which pay
the identical cost. Not a regression introduced by this round.
