---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-kgxf50-check-semantic-audit-ruff"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
command: "uv run python scripts/segmenter_semantic_audit.py --store data/segmenter; uv run ruff check .; uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-mechanical-verification"
summary: "segmenter_semantic_audit.py: 6 collapsed findings, all pre-existing and documented (doc_3b0be436... genuinely dropped out of this set once its second annotation existed -- see decision-preserve-audit-allowlist-precedent); none of the 3 new documents appear in any finding. ruff check: all checks passed (462 files). ruff format --check: 462 files already formatted."
---

# Check: semantic audit + lint, post-ingestion

```
$ uv run python scripts/segmenter_semantic_audit.py --store data/segmenter | grep "^Document:"
Document: doc_12f989ac213c5eadf857aacc69b33ad2
Document: doc_2a07306d88d1acebcdc0aff9958f7009
Document: doc_3cffd7961e9fc910f6ae628f5aaa6c40
Document: doc_d61aecbf08b525a26f908f655285fe6c
Document: doc_db852d2ad03c021f0ac411e3e5b63b60
Document: doc_f985597a64cc7b5ad06731c072915a7a

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
462 files already formatted
```
