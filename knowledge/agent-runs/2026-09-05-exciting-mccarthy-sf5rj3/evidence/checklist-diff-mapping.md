---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-sf5rj3-evidence-checklist-diff-mapping"
run_id: "2026-09-05-exciting-mccarthy-sf5rj3"
goal_id: "2026-09-05-exciting-mccarthy-sf5rj3-goal-close-1052-eval-harness-already-built"
kind: "diff"
reference: "src/segmenter_dataset/model_eval.py, src/segmenter_dataset/region_eval.py, scripts/run_segmenter_test_eval.py, src/segmenter_dataset/schemas.py (ModelAcceptanceEvidence/ModelCard/ExperimentManifest); git log --all for PRs #1090, #1092, #1099, #1101, #1104, #1126"
summary: "Line-by-line mapping of every #1052 checklist bullet to already-merged, already-tested code: exact-span P/R/F1 and per-category counts -> per_category_metrics; macro-F1 over a fixed target-category denominator (the #1048 inflation-bug fix) -> macro_f1_over_target_categories; micro metrics -> micro_metrics/MicroMetrics; relaxed overlap diagnostics -> relaxed_span_metrics/RelaxedSpanMetrics; category-vs-boundary error split -> classify_span_errors/SpanErrorBreakdown; region boundary error/IoU -> RegionComparison; matched vs. missed vs. hallucinated -> RegionTypeMetrics; structural anomaly detection (inverted inicio/fim pairs) -> detect_inverted_regions/StructuralAnomaly; document-level bootstrap CIs -> bootstrap_diff_ci_low and bootstrap_region_metric_ci_low; per-tribunal/document-type breakdowns gated on document-count support -> breakdown_by_group/region_breakdown_by_group (PR #1090), wired into scripts/run_segmenter_test_eval.py's _print_group_breakdown/_print_region_group_breakdown; human-readable plus machine-readable reports written side by side in run_segmenter_test_eval.py -> render_error_report (PR #1099) and render_region_report (PR #1092); model/run identity distinguishing a canonical baseline from a local ablation -> ExperimentManifest.opf_commit/checkpoint_selection/hyperparameters (PR #1101, PR #1104 'classify runs as canonical baseline vs local ablation') plus ModelCard.release_id/dataset_release_id/experiment_id/test_result_hash. None of these six merging PRs referenced #1052 by number in their commit titles, which is why okf/GitHub's auto-close-on-merge never fired."
---

# Evidência — mapeamento do checklist da #1052 para o código já mergeado

Cada item do checklist da issue tem uma função/classe correspondente já implementada e testada em `main`, construída por seis PRs já mergeados que nunca citaram `#1052` no título.
