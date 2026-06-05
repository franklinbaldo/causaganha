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