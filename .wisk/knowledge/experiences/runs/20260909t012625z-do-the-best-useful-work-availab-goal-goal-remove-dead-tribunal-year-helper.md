---
goal: "Remove candidates.py's dead tribunal_years_needing_consolidation_from_ia and add a module-surface regression-guard test, per the last round's confirmed next_move lead."
id: "run-goals/20260909t012625z-do-the-best-useful-work-availab/goal-remove-dead-tribunal-year-helper"
kind: "task-advance"
rationale: "Repo-wide grep confirms zero callers and zero tests for this function anywhere (src/, tests/, scripts/, docs/, workflows). It duplicates the item_id-parsing job dates_needing_consolidation_from_ia already does but with a latent bug: split_part(item_id, '-', -2) mis-parses hyphenated tribunal codes like TRE-* (e.g. djen-tre-ro-2025 would yield tribunal='ro' instead of 'tre-ro'). Matches this session-family's established pattern (7+ prior instances): dead code with a real bug should be deleted, not repaired, once every call site is grep-verified absent."
run: "runs/20260909T012625Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "candidates.py no longer defines tribunal_years_needing_consolidation_from_ia; a new RED test (module surface assertion) fails before the deletion and passes after; full pytest suite and ruff stay green; PR opened."
type: "RunGoal"
---

# RunGoal
