---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-bomtmk-check-semantic-audit-ruff"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
command: "uv run python scripts/segmenter_semantic_audit.py ; uv run ruff check ; uv run ruff format --check"
result: "passed"
summary: "Semantic audit: 6 findings, unchanged from the pre-round baseline (same 6 pre-existing allowlisted documents; none of the 3 new documents this round implicated). ruff check: all checks passed. ruff format --check: 462 files already formatted."
---

# Check: semantic audit + ruff after ingestion

```
$ uv run python scripts/segmenter_semantic_audit.py
Semantic Audit Findings:
Document: doc_12f989ac213c5eadf857aacc69b33ad2 [HIGH] fundamentacao_legal_collapsed
Document: doc_2a07306d88d1acebcdc0aff9958f7009 [HIGH] valor_condenacao_collapsed
Document: doc_3cffd7961e9fc910f6ae628f5aaa6c40 [HIGH] fundamentacao_legal_collapsed
Document: doc_d61aecbf08b525a26f908f655285fe6c [HIGH] valor_condenacao_collapsed
Document: doc_db852d2ad03c021f0ac411e3e5b63b60 [HIGH] fundamentacao_legal_collapsed
Document: doc_f985597a64cc7b5ad06731c072915a7a [HIGH] fundamentacao_legal_collapsed

$ uv run ruff check
All checks passed!

$ uv run ruff format --check
462 files already formatted
```
