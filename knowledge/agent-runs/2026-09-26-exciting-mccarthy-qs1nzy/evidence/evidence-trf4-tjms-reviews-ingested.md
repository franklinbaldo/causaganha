---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-qs1nzy-evidence-trf4-tjms-reviews-ingested"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
goal_id: "2026-09-26-exciting-mccarthy-qs1nzy-goal-1051-continue-adjudication"
kind: "runtime"
reference: "data/segmenter/reviews/doc_6b9ee9d4f525b8442af4cbc20da41269/rev_14388657a3b98d8b771bdf9364c351c6.xml, data/segmenter/reviews/doc_c41321b105269252919a5d4d730800a2/rev_4eb9b113da36de98b2bfcbd7fc9677dd.xml"
summary: "Two accepted ReviewRecords written after mechanical repair and adjudication of genuinely independent second annotations. scripts/segmenter_governance_status.py: review_count 48->50, test_count 18->20 (val_count unchanged at 30, its RFC 0012 ceiling), exactly matching the pre-annotation joint simulation."
---

# Evidence: two more #1051 documents adjudicated

```
$ uv run python scripts/segmenter_adjudication_candidates.py --top 1 \
    --simulate doc_6b9ee9d4f525b8442af4cbc20da41269 doc_c41321b105269252919a5d4d730800a2
{
  "joint_simulation": {
    "document_ids": [
      "doc_6b9ee9d4f525b8442af4cbc20da41269",
      "doc_c41321b105269252919a5d4d730800a2"
    ],
    "val_count": 30,
    "test_count": 20
  }
}
```
(confirmed BEFORE any second annotation was dispatched, against the
post-#1678-merge store: `review_count=48`, `test_count=18`)

Two independent Agent-tool subagents (`model=haiku`) produced second
annotations. Both needed repair before ingestion:

- **TRF4** (`doc_6b9ee9d4f525b8442af4cbc20da41269`): first attempt
  fabricated a duplicate `ref_processual` span inside ementa item 1
  (text absent from the source at that location) and silently dropped
  the standalone "ACÓRDÃO" heading line — both real content defects,
  discarded without ingestion. A second, more explicit retry (warning
  specifically about both defects plus NBSP preservation) passed
  content-wise but still flattened several NBSP characters to regular
  spaces — a pure, position-preserving whitespace substitution (verified
  via `difflib.SequenceMatcher` opcodes: every mismatch was `replace`
  with equal-length spans), repaired by rebuilding the tagged XML from
  the ground-truth `document.text` at the annotation's own label offsets
  via `segmenter_dataset.store._labels_to_text_element` — never
  retyping or altering any tag content.
- **TJMS** (`doc_c41321b105269252919a5d4d730800a2`): retyped "negaram
  provimento ao recurso" a second time as the `acordao_decisorio_fim`
  tag's content instead of wrapping the existing occurrence (the
  guideline's own documented anti-pattern: "never retype or duplicate
  it"). Repaired structurally by nesting the existing `resultado` span
  inside a `fim` wrapper closing at "ao recurso" (splitting `resultado`
  down to just "negaram provimento" to avoid overlap — also a better
  fit for Rule 3's "operative verb" than either annotator's original
  span).

Both repairs were verified via
`segmenter_dataset.store._text_element_to_labels` (verbatim-fidelity
reconstruction, exact match against `doc.text`) and
`segmenter_dataset.mechanical.validate_record` (zero problems, after
`drop_excluded_categories` removes the intentionally non-trainable
`ref_normativa`) before being ingested via
`scripts/annotate_second_independent.py`.

Both first annotations (`model_family=prompt_subagents:general-purpose`,
from the original corpus batch) had independently omitted `cabecalho`
entirely; both reviews adopted the second annotation's `cabecalho`
tagging. TRF4's review kept the first annotation's `ementa_fim` (a
correctly-identified closing cue the second annotation left unmatched).
Full per-document reasoning is in each `ReviewRecord`'s own
`resolution` field.

```
$ uv run python scripts/segmenter_governance_status.py
{
  "document_count": 197,
  "annotation_count": 273,
  "review_count": 50,
  "val_count": 30,
  "test_count": 20,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```

`scripts/segmenter_semantic_audit.py`: 6 findings, unchanged from the
pre-round baseline; neither new document implicated.
