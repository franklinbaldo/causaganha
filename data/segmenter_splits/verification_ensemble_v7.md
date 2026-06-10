# Verification Ensemble v7 — val+test gold verification protocol

This is the executable specification of the four-role verification ensemble
declared in `manifest.json` (`test_verified_by =
prompt_ensemble:strict+disambig+blind+adversarial`). It exists so the
verification that blessed the seed gold can be **reproduced exactly** when
scaling annotation (ADR 0010, Phase 2). Mechanical comparison of role
outputs is done by `scripts/ensemble_compare.py`.

## When to run

Over **val + test splits only** (low volume, high leverage). Train relies on
the labeler + `opf_annotate.py validate` mechanical checks.

## Model assignment

- All four roles run on a **strong model (Sonnet or better)** — never the
  same tier as the bulk labeler (Haiku). Model heterogeneity is the point:
  labeler and verifier errors must decorrelate.
- Each role runs as an **independent subagent with a fresh context**. Never
  share one conversation across roles — that correlates their errors.

## The four roles

Every role receives the document text. Roles 1, 2, and 4 also receive the
candidate annotations; role 3 does not (blind). Each role returns spans as
`{category, match, nth}` (shortest *unique* match preferred), resolved to
offsets with `opf_annotate.py from-spans` and checked with `validate`.

### Role 1 — strict-boundary

> You are verifying span BOUNDARIES only. For each annotated span, check:
> (a) `text[start:end]` is the shortest surface that uniquely identifies the
> anchor cue; (b) no leading/trailing whitespace; (c) single-anchor spans are
> ≤120 chars and 1–5 words typical; (d) paired `_inicio`/`_fim` marks the
> CUE, not the region. Do not question the category choice. Output: for each
> span, either CONFIRM or a corrected `{category, match, nth}`.

### Role 2 — category-disambiguation

> You are verifying span CATEGORIES only, taking boundaries as given. Apply
> the guideline's contrast rules: `dispositivo_abertura` vs interlocutory
> "Decido"; `resultado` only on the operative verb after the dispositivo;
> `fundamentacao_legal` vs (unlabeled) `ref_normativa`; in acórdãos, the
> collegiate result is `acordao_decisorio_*`, never a `dispositivo_abertura`
> inside a `voto`. Output: for each span, CONFIRM or the corrected category.

### Role 3 — blind-relabel

> Annotate this document from scratch following
> `annotation_guideline_v7.md`. You have NOT seen any existing annotation.
> Return all spans as `{category, match, nth}`. Do not annotate
> `ref_normativa`.

The blind output is compared against the candidate set with
`ensemble_compare.py`; disagreements (missing, extra, boundary, category)
become adjudication items.

### Role 4 — adversarial

> Your job is to FIND ERRORS in this annotation. Actively hunt for: a second
> operative `dispositivo_abertura`; `resultado` on a reasoning or quoted
> verb; a missed `preliminar`/`custas`/`honorarios` section; an `_inicio`
> without its real `_fim` when one exists in the text; acórdão categories in
> a sentença or vice versa. Report each suspected error with the evidence
> quote. Finding nothing is an acceptable outcome — do not invent errors.

## Adjudication

1. Run all four roles; collect role outputs as JSONL (same record order as
   the split under verification).
2. Run `scripts/ensemble_compare.py reference.jsonl role1.jsonl
   role3.jsonl ...` — it reports per-document, per-category disagreement and
   exits non-zero while any remain.
3. Every disagreement is adjudicated by a strong model (or human) with the
   guideline open; the adjudicated decision is applied to the gold and the
   compare is re-run until clean.
4. Any document the **bulk labeler flagged as ambiguous** during annotation
   is adjudicated by the strong model even if the ensemble agrees (ADR 0010
   tiered-assignment rule).

## Recording the result

On success update `manifest.json`:

```json
"test_verified_by": "prompt_ensemble:strict+disambig+blind+adversarial",
"verifier_model": "<model used>"
```

Never set `test_verified_by` to the ensemble value without actually running
all four roles — `same_as_train_labeler` is the honest placeholder.
