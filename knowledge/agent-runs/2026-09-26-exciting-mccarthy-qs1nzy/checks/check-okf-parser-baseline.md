---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-qs1nzy-check-okf-parser-baseline"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal_id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-formalize-candidate-selection"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Baseline check before this round's own writes: conformant, 0 diagnostics, 2580 concepts. HEAD at 103ad9b (round uq3be8's merge, PR #1677). Two open PRs found (#1678, #1679), both from concurrent rounds with real Agent-tool access working the same issue -- neither mine to merge."
---

# Check: okf-parser baseline before this round's writes

```
{
  "concept_count": 2580,
  "conformant": true,
  "diagnostics": [],
  "markdown_count": 2583,
  "reserved_count": 3,
  "root": "/home/user/causaganha/knowledge"
}
```

`scripts/segmenter_governance_status.py` at the same moment:

```
{
  "document_count": 197,
  "annotation_count": 266,
  "review_count": 43,
  "val_count": 30,
  "test_count": 13,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```
