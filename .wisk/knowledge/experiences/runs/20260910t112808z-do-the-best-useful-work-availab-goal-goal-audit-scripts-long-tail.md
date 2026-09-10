---
goal: "Audit the untested long-tail of scripts/*.py named in run 20260910T102506Z's own next_move (analyze_with_rag.py, annotate_with_llm.py, augment_segmenter_data.py, batch_embed_decisions.py, bootstrap_training_corpus.py, build_gold_benchmark.py, classify_from_batch_embeddings.py, daily_benchmark_update.py, evaluate_regex_segmenter.py, generate_homepage_widgets.py, ia_practicality_probe.py, roundtrip_check.py, sample_ia_texts.py, snapshot_parquets_for_rollback.py, stress_test_djen.py, train_decision_segmenter.py, validate_manifest.py, vendor_pje_swagger.py) for a genuine behavioral defect, fix it via RED->GREEN TDD, and open a PR."
id: "run-goals/20260910t112808z-do-the-best-useful-work-availab/goal-audit-scripts-long-tail"
kind: "task-advance"
rationale: "Explicit next_move from run-outcomes/20260910t102506z-do-the-best-useful-work-availab/outcome-final: src/tcu_acordaos and src/causaganha_cli are now confirmed swept clean, narrowing remaining unaudited surface to this scripts/*.py long tail. Re-verified via repo-wide grep just now that all 17 of these scripts (excluding opf_annotate.py and ref_normativa_prepass.py, which do have test references) still have zero references anywhere under tests/, confirming the prior round's naming is still accurate and not yet picked up by any intervening round."
run: "runs/20260910T112808Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "Either (a) a RED test demonstrating a real behavioral defect in one of the audited scripts, followed by a minimal fix turning it GREEN, full pytest+ruff clean, and a PR opened; or (b) if the audit finds no defect worth a behavior-changing PR, explicit negative evidence naming which scripts were read and why nothing warranted a change, plus a concretely narrowed next audit target."
type: "RunGoal"
---

# RunGoal
