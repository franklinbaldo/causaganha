---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-qs1nzy-check-pytest-full-suite"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal_id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-formalize-candidate-selection"
command: "uv run pytest -q"
result: "passed"
summary: "Full repository suite green: 2040 collected tests, 0 in .pytest_cache/v/cache/lastfailed, ~16 minutes wall time (12:56-13:12 UTC). Slowness is a pre-existing characteristic of tests/segmenter_dataset's ~18 test_real_store_reflects_* tests plus this round's own new live-store test, each independently paying segmenter_dataset.splits.build_groups' ~75s near-duplicate scan over the 197-document store (confirmed by direct benchmark) -- not a regression from this round's changes."
---

# Check: full repository test suite

```
$ nohup uv run pytest -q > full_pytest_run1.log 2>&1 &
... (backgrounded; monitored via `while kill -0 $PID; do sleep 5; done`)
... 2040 tests, dots + 1 skip, no failures, [100%]

$ cat .pytest_cache/v/cache/lastfailed
{}

$ python3 -c "import json; print(len(json.load(open('.pytest_cache/v/cache/nodeids'))))"
2040
```

Direct benchmark confirming the root cause of the suite's wall-clock cost
(not a regression -- a pre-existing property of the segmenter test
suite at this corpus size):

```
$ uv run python -c "
from pathlib import Path
from segmenter_dataset.store import SegmenterDatasetStore
from segmenter_dataset.splits import GroupingKeys, build_groups
store = SegmenterDatasetStore(Path('data/segmenter'))
documents = list(store.list_documents())
grouping_keys = [GroupingKeys.from_document(doc) for doc in documents]
groups = build_groups(documents, grouping_keys)   # ~75s, O(n^2)-pruned
                                                    # near-dup scan
"
build_groups 74.85203170776367 ngroups 191
```

`tests/segmenter_dataset/test_segmenter_governance_status.py` alone has
~18 `test_real_store_reflects_*` tests that each independently call this
path once (plus this round's own new
`test_real_store_candidate_scan_is_consistent_with_governance_status`,
which calls it twice) -- accounting for the bulk of the suite's ~16
minute wall time. Ran once, full and green; not re-run a second time
given its cost and the confirmed zero-failure result.

