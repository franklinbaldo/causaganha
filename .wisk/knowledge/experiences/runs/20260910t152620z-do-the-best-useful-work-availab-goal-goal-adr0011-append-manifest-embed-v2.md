---
type: "RunGoal"
id: "run-goals/20260910t152620z-do-the-best-useful-work-availab/goal-adr0011-append-manifest-embed-v2"
run: "runs/20260910T152620Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Continue the ADR-0011 except-Exception audit named as this loop's next_move: classify the bare 'except Exception' sites in scripts/append_manifest.py (2 sites) and scripts/pipeline/embed_v2.py (1 site) as genuine per-item worker-pool bulkheads (cite the ADR) or single-shot CLI catch-alls (narrow to specific exception types), then enforce the decision with a test extension."
rationale: "The prior round's RunOutcome (runs/20260910T134021Z.../outcome-final) found ~23 more un-audited bare except-Exception sites across 8 scripts/ files after fixing annotate_with_llm.py in PR #1423, and named this as the natural next slice. No open PR needs resuming (only a dependabot devDependency bump PR #1353 is open) and all 16 open GitHub issues are the same deprioritized/blocked segmenter-research backlog verified in knowledge/backlog/. Auditing two small, fully-read files keeps the round TDD-able and reviewable instead of a mechanical blanket fix across all 8 files."
success_signal: "tests/test_except_exception_policy.py gains a RED test that fails against current scripts/append_manifest.py and scripts/pipeline/embed_v2.py, then goes GREEN after: (a) append_manifest.py's two sites are narrowed to specific exception types (no bare 'except Exception' remains there), and (b) embed_v2.py's upload_embeddings_to_ia bulkhead gets a docs/adr/0011 citation comment. uv run pytest tests/test_except_exception_policy.py and uv run ruff check both pass, and the change ships as a merged PR."
status: "active"
---

# RunGoal
