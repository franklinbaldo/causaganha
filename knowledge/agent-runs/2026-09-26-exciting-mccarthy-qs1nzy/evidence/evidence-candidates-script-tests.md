---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-qs1nzy-evidence-candidates-script-tests"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal_id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-formalize-candidate-selection"
kind: "test_green"
reference: "scripts/segmenter_adjudication_candidates.py, tests/segmenter_dataset/test_segmenter_adjudication_candidates.py"
summary: "New module + 5 tests, all green: 4 synthetic-store unit tests (exclusion rules for multi-annotated/seeded/already-reviewed documents; the individually-raises-test-count signal; joint_simulation matching governance_status on a fabricated store) plus 1 live-store cross-check confirming the packaged code reproduces exactly the numbers this round's own scratch script (and 6 prior rounds' throwaway equivalents) computed by hand: 130 candidates, base val_count=30/test_count=13."
---

# Evidence: new candidate-selection script, tests green

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_adjudication_candidates.py
.....                                                                    [100%]
5 passed
```

Live-store numbers the new module computes (matching
`scripts/segmenter_governance_status.py` and this round's scratch
simulation exactly, before PR #1678/#1679 landed):

```
$ uv run python -c "
import sys; sys.path.insert(0, 'scripts')
import segmenter_adjudication_candidates as m
from pathlib import Path
candidates = m.find_second_annotation_candidates(Path('data/segmenter'))
print('candidates', len(candidates))
"
candidates 130   # (74s -- dominated by segmenter_dataset.dedup's O(n^2)-pruned
                 # near-duplicate scan inside splits.build_groups, run once;
                 # same cost every scripts/segmenter_governance_status.py call
                 # and every one of the 18 existing test_real_store_* tests
                 # already pays)
```

123 of the 130 candidates individually raise `test_count` in isolation
(same figure the scratch script in
`decisions/decision-subagent-tool-unavailable.md`'s sibling scratch run
found before this round discovered the subagent blocker). The two
shortest -- `doc_6b9ee9d4f525b8442af4cbc20da41269` (TRF4, acordao, 2477
chars) and `doc_c41321b105269252919a5d4d730800a2` (TJMS, acordao, 2508
chars) -- jointly raise `test_count` from 13 to 15 (`val_count` unchanged
at 30). These are recorded in `knowledge/backlog/issue-1051.md` as the
ready-to-go pick for the next round that does have Agent-tool access, so
that round can skip the scan/simulate steps entirely and go straight to
dispatching the two subagents.

`uv run ruff check` / `uv run ruff format --check` on the 2 new files:
clean.
