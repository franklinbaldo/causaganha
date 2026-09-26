---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-bomtmk-reading-okf"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1051.md, knowledge/backlog/issue-1050.md, .claude/agent-run-scaffold.md, uv run okf-parser check knowledge --relational-schema okf.schema.sql"
finding: "OKF bundle conformant at session start (0 diagnostics, 2563 concepts). issue-1051.md's backlog narrative (updated by round kgxf50, last_verified_at 2026-09-26T07:00:00Z) is the authoritative operational method for this round's work: scan single-annotated/seeded_with=='none'/unreviewed candidates, SIMULATE assign_splits before annotating, dispatch a genuinely independent second annotation via Agent tool (model=haiku, distinct model_family), verify mechanically before writing, adjudicate against the guideline's own rules, and re-run the FULL test suite before finalizing (not just tests/segmenter_dataset) -- a process lesson kgxf50 learned only because a full-suite run caught a near-mistake."
---

# Reading: knowledge OKF bundle

Ran `uv run okf-parser check knowledge --relational-schema okf.schema.sql`
at session start: conformant, 0 diagnostics, 2563 concepts (see
`checks/check-okf-parser-baseline.md`).

Read `knowledge/backlog/issue-1051.md` in full (the dedicated backlog
file for this round's chosen goal, first created by round `p08457` and
extended by every #1051 round since). It documents, as an explicit,
reusable method:

1. Scan for candidates: single-annotated, `seeded_with=='none'`,
   unreviewed documents (a document whose sole annotation has
   `seeded_with != 'none'` can never be adjudicated — filter it out).
2. **Simulate** `assign_splits` with each candidate added to
   `evaluation_eligible`, in isolation and then jointly with the
   round's actual batch, *before* spending any annotation effort —
   `assign_splits` recomputes the whole val/test partition from a fixed
   hash order of `(seed, group_id)` every call, so which specific
   document lands in val vs. test is not identity-controllable; only
   the aggregate `test_count`/`val_count` is the real, checkable
   contract.
3. Dispatch a genuinely independent second annotation via the Agent
   tool with `model=haiku` (`model_family=prompt_subagents:haiku`,
   distinct from the first annotation's
   `model_family=prompt_subagents:general-purpose`, satisfying
   `NonIndependentReviewError`'s guard), without exposing the first
   annotation to the subagent.
4. Verify mechanically (`_text_element_to_labels` verbatim-fidelity
   reconstruction + `mechanical.validate_record`) *before* writing
   anything to the store — round `kgxf50` found real defects this way
   (silently dropped NBSP whitespace, an XML-nesting overlap bug), all
   fixed without ever looking at the first annotation's content.
5. Adjudicate as reviewer: compare disagreements against the
   guideline's own rules, not by picking one side wholesale.
6. Re-run the **full** repository test suite (not just
   `tests/segmenter_dataset`) before finalizing — round `kgxf50`'s own
   process lesson, since a pre-existing, document-specific precedent
   test elsewhere in the suite once caught a genuine adjudication
   mistake this way.

Also read `.claude/agent-run-scaffold.md` (this run's own operational
contract — scaffold → okf-parser check → fill next required state →
work → evidence → check again) and `knowledge/backlog/issue-1050.md`
(confirms the corpus-scale ceiling reached 30/30 at round `ku8qje`, so
no further corpus growth is required to keep advancing #1051).
