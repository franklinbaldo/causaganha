---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-sg2540-check-semantic-audit-ruff"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
command: "uv run python scripts/segmenter_semantic_audit.py; uv run ruff check; uv run ruff format --check"
result: "passed"
summary: "6 semantic-audit findings total, matching the pre-round baseline exactly (none of this round's 4 documents implicated after fixing a transient long_anchor finding on TJPI mid-round). ruff check/format --check both clean across 462 files."
---

# Check: semantic audit clean, ruff clean

`scripts/segmenter_semantic_audit.py`: 6 findings total (documents
`doc_12f989ac213c5eadf857aacc69b33ad2`, `doc_2a07306d88d1acebcdc0aff9958f7009`,
`doc_3cffd7961e9fc910f6ae628f5aaa6c40`, `doc_d61aecbf08b525a26f908f655285fe6c`,
`doc_db852d2ad03c021f0ac411e3e5b63b60`, `doc_f985597a64cc7b5ad06731c072915a7a`)
-- matching the pre-round baseline count (6), none of this round's 4
new documents implicated. A first run had flagged a 5th, NEW
`long_anchor` finding on this round's own
`doc_7e91843200b79e7467d0ae541ad9c6c8` (TJPI) second annotation
(211-char `relatorio_inicio`); fixed by deleting and re-ingesting that
document's annotation+review with a tight span before this final run
(see `decision-adjudication-resolutions.md`).

```
$ uv run ruff check
All checks passed!
$ uv run ruff format --check
462 files already formatted
```
