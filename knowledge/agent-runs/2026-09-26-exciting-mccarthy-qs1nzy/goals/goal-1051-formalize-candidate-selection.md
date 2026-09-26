---
type: AgentGoal
id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-formalize-candidate-selection"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal: "Since this session cannot dispatch an independent-annotation subagent (hard tooling blocker, distinct from every prior #1051 round), commit the #1051 candidate-selection method -- the assign_splits simulation every prior round re-derived via a throwaway scratch script -- as tested, reusable code (scripts/segmenter_adjudication_candidates.py), instead of fabricating a fake independent annotation or doing nothing."
rationale: "scripts/segmenter_governance_status.py, run live at round start, confirms document_count=197/review_count=43/val_count=30 (at ceiling)/test_count=13 -- identical to round uq3be8's final numbers. This round's established next step (dispatch an Agent-tool subagent, model=haiku, for a genuinely independent second annotation) is not executable here: no Task/Agent tool is present in this session's tool surface, and a nested `claude -p --model haiku` subprocess was denied by the environment's own auto-mode classifier ([Create Unsafe Agents]), with an explicit instruction not to retry via other flags/tools/hosts. Fabricating a second annotation myself under a different model_family label would misrepresent provenance in a dataset whose whole purpose is genuine inter-annotator independence for model selection (RFC 0012 Sec 5.3) -- worse than making no numeric progress this round. Meanwhile every one of the 6 prior same-day rounds (ns7mbo/ku8qje/p08457/kgxf50/bomtmk/uq3be8) wrote and discarded an equivalent scratch script to answer 'which candidates are actually worth annotating' -- a real, recurring cost this round can remove for every future round, including ones that do have Agent-tool access."
success_signal: "scripts/segmenter_adjudication_candidates.py exists with find_second_annotation_candidates() and joint_simulation(), covered by tests/segmenter_dataset/test_segmenter_adjudication_candidates.py (synthetic-store unit tests for the exclusion rules and the raises/does-not-raise signal, plus a live-store cross-check asserting its output matches scripts/segmenter_governance_status.py's val_count/test_count exactly); uv run pytest -q (full suite) green; uv run ruff check/format --check clean; okf-parser check conformant; knowledge/backlog/issue-1051.md updated with this round's honest narrative (no test_count movement, blocker documented, tooling contributed); changes committed, pushed, PR opened referencing #1051 as continuity, not closure; PR left open (not merged) for human review."
status: "achieved"
---

# Goal: formalize #1051's candidate-selection method (this round's actual deliverable)

This round could not advance `test_count` -- the numeric floor #1051
rounds have chased all day -- because the mechanism every prior round
used to get a second, independent annotation (an Agent-tool subagent)
is not available in this session, and the one substitute attempted (a
nested `claude` CLI process) was explicitly denied by the environment's
own safety classifier as "Create Unsafe Agents," with instructions not
to retry via another route. Rather than force the number up dishonestly
or hand back an empty round, this goal commits the *other* half of the
established method -- the "simulate before you annotate" candidate scan
against `assign_splits` -- as tested, reusable code that every future
round (including ones with real subagent access) can call instead of
re-deriving it from scratch, as 6 rounds in a row have done.
