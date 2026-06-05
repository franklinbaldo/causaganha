# 10. Rebuild Segmenter Pipeline v7

Date: 2026-06-05

## Status

Accepted

## Context

The v6 Decision Segmenter relied on a gold dataset generated through heuristics and legacy annotations. While this dataset served its purpose for earlier iterations, it has become a bottleneck for improving model accuracy. The legacy dataset contains unverified annotations and biases introduced by the heuristics, limiting the potential of our models.

We recently observed significant success with the "Leizilla #84" strategy, which employed a clean, subagent-driven annotation loop to build high-quality datasets from scratch.

To advance the segmenter to v7, we have developed new infrastructure and updated our ontology. The trained label space has 22 entries (`O` + 5 single-anchor + 16 paired `_inicio`/`_fim`); `ref_normativa` is excluded and handled by a regex pre-pass at inference. To fully leverage these improvements, we need a pristine gold dataset.

## Decision

We have decided to rebuild the v7 Decision Segmenter pipeline from scratch, specifically focusing on the gold dataset generation.

1.  **Salvage v7 Infrastructure**: We will retain the modern v7 infrastructure, scripts, tests, and configurations (e.g., sampler logic, region reconstruction, regex pre-pass, OPF annotation helpers, and the 22-entry trained label space) developed in earlier iterations.
2.  **Discard Legacy Data**: We will intentionally discard all pre-existing v6 gold data splits (`train.jsonl`, `val.jsonl`, `test.jsonl`, `manifest.json`).
3.  **Clean Annotation Loop**: We will regenerate all gold splits from zero using a clean subagent flow modeled directly after the successful "Leizilla #84" strategy. This will ensure our new dataset is free from legacy heuristic biases and fully aligned with the v7 annotation guidelines.

## Consequences

*   **Positive**: We will obtain a high-quality, verified gold dataset tailored to the v7 ontology. This is expected to significantly improve the accuracy and robustness of the Decision Segmenter.
*   **Positive**: The clean separation of code and data allows us to iterate on the infrastructure independently of the dataset state.
*   **Negative**: There is an initial cost to re-annotate a full dataset from scratch. We will depend heavily on the subagent annotation loop performing well to populate the new dataset in a timely manner. We will not have a deployable v7 model until the new annotation loop completes.

## Phase 2 plan (gold build — deferred)

The infrastructure (Step 1) is merged and CI-green; the gold annotation
(Phase 2) is deferred to a dedicated effort. Two decisions are locked in for
when it runs:

1.  **Extend the ontology before annotating.** The current 22-entry trained
    label space (`O` + 5 single-anchor + 16 paired) covers structures shared by
    sentenças and acórdãos (e.g. `ementa_*`, `relatorio_*`, `capitulo_merito_*`)
    but has no acórdão-specific categories. Before sampling/annotating, add the
    acórdão pair categories — `voto_inicio`/`voto_fim` and
    `acordao_decisorio_inicio`/`acordao_decisorio_fim` — to
    `SPAN_CLASS_NAMES_V7`, `label_space.json`, the annotation guideline, and the
    count assertions (`tests/test_privacy_filter_segmenter.py`,
    `scripts/test_opf_label_space.py`, the Colab notebook, this ADR). The pool
    MUST include acórdãos so these categories — and the rare
    `custas_*`/`honorarios_*`/`preliminar_*` ones — get real examples; otherwise
    they stay declared-but-unlearnable (the open `label_space.json` review
    thread). Categories that cannot be populated should be trimmed rather than
    declared empty.

2.  **Annotate via subagents, not an LLM-API script.** Shard the pool (acórdãos
    first); one labeling subagent per batch returns `{category, match, nth}` in
    document order; resolve offsets with `opf_annotate.py from-spans`. Enforce
    the one-operative-`dispositivo_abertura` rule and `resultado`-only-after-the-
    dispositivo rule. Do not annotate `ref_normativa` (regex pre-pass,
    `scripts/ref_normativa_prepass.py`). Verify val+test with a decorrelated
    four-role ensemble (strict-boundary, category-disambiguation, blind-relabel,
    adversarial) and set `manifest.test_verified_by` accordingly. Report
    macro-F1 both with and without `ref_normativa` to surface the v6 inflation.