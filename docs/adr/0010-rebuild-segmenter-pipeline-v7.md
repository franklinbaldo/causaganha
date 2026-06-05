# 10. Rebuild Segmenter Pipeline v7

Date: 2026-06-05

## Status

Accepted

## Context

The v6 Decision Segmenter relied on a gold dataset generated through heuristics and legacy annotations. While this dataset served its purpose for earlier iterations, it has become a bottleneck for improving model accuracy. The legacy dataset contains unverified annotations and biases introduced by the heuristics, limiting the potential of our models.

We recently observed significant success with the "Leizilla #84" strategy, which employed a clean, subagent-driven annotation loop to build high-quality datasets from scratch.

To advance the segmenter to v7, we have developed new infrastructure and updated our ontology. The trained label space has 26 entries (`O` + 5 single-anchor + 20 paired `_inicio`/`_fim`, including the acórdão-specific `voto_*` and `acordao_decisorio_*` pairs); `ref_normativa` is excluded and handled by a regex pre-pass at inference. To fully leverage these improvements, we need a pristine gold dataset.

## Decision

We have decided to rebuild the v7 Decision Segmenter pipeline from scratch, specifically focusing on the gold dataset generation.

1.  **Salvage v7 Infrastructure**: We will retain the modern v7 infrastructure, scripts, tests, and configurations (e.g., sampler logic, region reconstruction, regex pre-pass, OPF annotation helpers, and the 22-entry trained label space) developed in earlier iterations.
2.  **Discard Legacy Data**: We will intentionally discard all pre-existing v6 gold data splits (`train.jsonl`, `val.jsonl`, `test.jsonl`, `manifest.json`).
3.  **Clean Annotation Loop**: We will regenerate all gold splits from zero using a clean subagent flow modeled directly after the successful "Leizilla #84" strategy. This will ensure our new dataset is free from legacy heuristic biases and fully aligned with the v7 annotation guidelines.

## Consequences

*   **Positive**: We will obtain a high-quality, verified gold dataset tailored to the v7 ontology. This is expected to significantly improve the accuracy and robustness of the Decision Segmenter.
*   **Positive**: The clean separation of code and data allows us to iterate on the infrastructure independently of the dataset state.
*   **Negative**: There is an initial cost to re-annotate a full dataset from scratch. We will depend heavily on the subagent annotation loop performing well to populate the new dataset in a timely manner. We will not have a deployable v7 model until the new annotation loop completes.

## Phase 2 plan (gold build — seed committed)

The infrastructure (Step 1) is merged and CI-green. A first **seed gold** is
committed to `data/segmenter_splits/` (20 TJRO docs — 8 acórdão + 12 sentença,
189 spans, all 25 trained classes populated, `test_verified_by =
prompt_ensemble:strict+disambig+blind+adversarial`). It was built end-to-end the
subagent way below; the remaining work is to **scale** it (more tribunals, more
volume per rare class) — not to change the method. The governing decisions:

1.  **Extend the ontology before annotating — DONE.** The trained label space
    was grown from 22 to 26 entries (`O` + 5 single-anchor + 20 paired) by
    adding the acórdão pair categories `voto_inicio`/`voto_fim` and
    `acordao_decisorio_inicio`/`acordao_decisorio_fim` across
    `SPAN_CLASS_NAMES_V7`, the committed `label_space.json`, the annotation
    guideline, the count assertions (`tests/test_privacy_filter_segmenter.py`,
    `scripts/test_opf_label_space.py`), the Colab notebook, and this ADR. The
    pool MUST include genuine second-instance acórdãos so these categories — and
    the rare `custas_*`/`honorarios_*`/`preliminar_*` ones — get real examples;
    otherwise they stay declared-but-unlearnable (the open `label_space.json`
    review thread). Categories that cannot be populated should be trimmed rather
    than declared empty.

2.  **Annotate via subagents, not an LLM-API script.** Shard the pool (acórdãos
    first); one labeling subagent per batch returns `{category, match, nth}` in
    document order; resolve offsets with `opf_annotate.py from-spans`. Enforce
    the one-operative-`dispositivo_abertura` rule and `resultado`-only-after-the-
    dispositivo rule. Do not annotate `ref_normativa` (regex pre-pass,
    `scripts/ref_normativa_prepass.py`). Verify val+test with a decorrelated
    four-role ensemble (strict-boundary, category-disambiguation, blind-relabel,
    adversarial) and set `manifest.test_verified_by` accordingly. Report
    macro-F1 both with and without `ref_normativa` to surface the v6 inflation.

3.  **Tiered model assignment (to stay under usage limits).** The orchestrator
    spawns subagents with an explicit model per role:
    *   **Bulk labeling → Haiku.** The structural anchors are short, distinctive
        cues, so cheap models suffice. To neutralise Haiku's weakness at
        *counting occurrences*, labeling subagents must return the **shortest
        _unique_ `match`** (so `nth` is `1` and no counting is needed); a longer
        unique surface also forces them to locate the genuinely operative
        clause. `from-spans` + `validate` are the mechanical safety net (they
        fail loudly on match-not-found / overlap / whitespace), letting cheap
        models be wrong loudly rather than silently.
    *   **Verification ensemble → strong model (Sonnet/Opus).** It runs over
        val+test only (low volume, high leverage), so it does not threaten
        limits. Model heterogeneity between the Haiku labeler and a stronger
        blind-relabel verifier is a *feature*: their errors decorrelate, which
        is the whole point of the ensemble.
    *   Any document a Haiku labeler flags as ambiguous is re-adjudicated by the
        stronger model.