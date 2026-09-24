---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-khpkk2-check-full-suite-post-merge"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
goal_id: "2026-09-24-exciting-mccarthy-khpkk2-goal-land-batch26-resolve-stale-1600"
command: "uv run ruff check && uv run ruff format --check && uv run okf-parser check knowledge --relational-schema okf.schema.sql && uv run python scripts/segmenter_governance_status.py --store data/segmenter && uv run pytest -q"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-khpkk2-evidence-pr-1603-merged"
summary: "Todos os checks executados apos o merge de #1603 e a reconciliacao do conflito em issue-1050.md: ruff/format limpos, okf-parser conformante (2098 conceitos, 0 diagnosticos), governance_status.py em 0m57.4s com document_count=193, pytest completo sem falhas."
---

# Check: suite completa pos-merge de #1603

```
$ uv run ruff check
All checks passed!
$ uv run ruff format --check
454 files already formatted
$ uv run okf-parser check knowledge --relational-schema okf.schema.sql
{"conformant": true, "diagnostics": [], "concept_count": 2098, "markdown_count": 2101, "reserved_count": 3}
$ time uv run python scripts/segmenter_governance_status.py --store data/segmenter
{"document_count": 193, "annotation_count": 246, "val_ceiling_at_full_adjudication": 29, "test_ceiling_at_full_adjudication": 29, ...}
real  0m57.414s
$ uv run pytest -q
(sem falhas)
```
