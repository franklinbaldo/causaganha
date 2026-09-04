#!/usr/bin/env python3
r"""Evaluate the CausaGanha segmenter against the locked test set -- EXACTLY ONCE.

This is the separately gated step RFC 0012 §3.3/§13.1 requires: training
(`scripts/run_segmenter_training.py`) never touches `test.jsonl`; this
script is the only place that does, and it is meant to run once per model
release, not per commit. It refuses to run without an explicit
`--i-understand-this-consumes-the-locked-test-set` flag, and refuses to
overwrite an existing model card without `--force` -- neither is real
cryptographic locking (RFC 0012 §13.2's `age`/`gpg`-encrypted test blob is
still TODO), but both make an accidental second "final" evaluation loud
instead of silent.

Computes, against the RFC 0012 §16.2 gate:

- macro-F1(model) vs. macro-F1(trivial baseline) on the same locked test
  set, with a document-level bootstrap 95% CI of the difference
  (`segmenter_dataset.model_eval`);
- point-estimate floor on the four RFC-fixed critical categories.

...and writes a `ModelCard` (distinct from the dataset's `ReleaseManifest`)
recording that evidence plus who/when unlocked the test set and a hash of
the result, per RFC 0012 §13.2's "registered operation" requirement.

Usage:
    uv run python scripts/run_segmenter_test_eval.py \
        --experiment-manifest training-runs/segmenter-real-v8.1/experiment_manifest.json \
        --data-dir dataset-releases/segmenter-real-v8.1/opf-export \
        --dataset-release-id segmenter-real-v8.1 \
        --model-release-id segmenter-model-v8.1 \
        --output-dir model-releases/segmenter-model-v8.1 \
        --executor "$(whoami)" \
        --i-understand-this-consumes-the-locked-test-set

Not runnable in this environment (no `opf`/`transformers` inference
available, and no val/test data exists yet) -- written ahead of time per
explicit instruction; run once a real locked test set and trained
checkpoint exist. Confirm the `transformers` token-classification pipeline
call against the actual `opf` checkpoint format before the first real run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog

from segmenter_dataset.model_eval import (
    DocumentModelPrediction,
    breakdown_by_group,
    evaluate_model_acceptance,
)
from segmenter_dataset.region_eval import region_breakdown_by_group, render_region_report
from segmenter_dataset.schemas import ExperimentManifest, Label, ModelCard


logger = structlog.get_logger()


def _detect_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _load_test_jsonl(path: Path) -> tuple[list[str], dict[str, tuple[Label, ...]], dict[str, str]]:
    document_ids: list[str] = []
    gold_by_document: dict[str, tuple[Label, ...]] = {}
    text_by_document: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        document_id = record["info"]["document_id"]
        labels = tuple(
            Label(start=item["start"], end=item["end"], category=item["category"])
            for item in record["label"]
        )
        document_ids.append(document_id)
        gold_by_document[document_id] = labels
        text_by_document[document_id] = record["text"]
    return document_ids, gold_by_document, text_by_document


def _load_document_groups(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Tribunal/document_type per document_id, from the same test.jsonl ``info`` block.

    ``opf_export.py``'s ``to_opf_record`` already writes this metadata into
    every record; a document whose ``info`` omits a key is skipped for that
    dimension rather than defaulted to a placeholder, so ``breakdown_by_group``
    reports it as "no known group" instead of manufacturing a fake one.
    """
    tribunal_by_document: dict[str, str] = {}
    document_type_by_document: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        info = record["info"]
        document_id = info["document_id"]
        if "tribunal" in info:
            tribunal_by_document[document_id] = info["tribunal"]
        if "document_type" in info:
            document_type_by_document[document_id] = info["document_type"]
    return tribunal_by_document, document_type_by_document


def _print_group_breakdown(
    title: str, predictions: list[DocumentModelPrediction], group_of_document: dict[str, str]
) -> None:
    breakdown = breakdown_by_group(predictions, group_of_document)
    if not breakdown:
        return
    print(f"breakdown by {title}:")
    for group, metrics in breakdown.items():
        if metrics.macro_f1 is None:
            print(f"  {group}: documents={metrics.document_count} (too few for a group macro-F1)")
        else:
            print(
                f"  {group}: documents={metrics.document_count} "
                f"macro_f1={metrics.macro_f1:.3f} micro_f1={metrics.micro.f1:.3f}"
            )


def _write_region_report(predictions: list[DocumentModelPrediction], output_dir: Path) -> Path:
    """Write #1052's region-level report (match rate, IoU, structural anomalies) alongside the model card.

    Diagnostic only -- unlike ``evaluate_model_acceptance``'s span-level
    evidence, nothing here feeds ``eligible_for_deploy``, per #1052's
    "without pretending to prove semantic correctness."
    """
    report_path = output_dir / "region_report.txt"
    report_path.write_text(render_region_report(predictions), encoding="utf-8")
    return report_path


def _print_region_group_breakdown(
    title: str, predictions: list[DocumentModelPrediction], group_of_document: dict[str, str]
) -> None:
    breakdown = region_breakdown_by_group(predictions, group_of_document)
    if not breakdown:
        return
    print(f"region breakdown by {title}:")
    for group, metrics in breakdown.items():
        if metrics.regions is None:
            print(f"  {group}: documents={metrics.document_count} (too few for region metrics)")
        else:
            for base, region_metrics in metrics.regions.items():
                print(
                    f"  {group}/{base}: documents={metrics.document_count} "
                    f"match_rate={region_metrics.match_rate}"
                )


def _run_opf_inference(
    text_by_document: dict[str, str], checkpoint_dir: Path, device: str
) -> dict[str, tuple[Label, ...]]:
    """Span predictions per document via a token-classification pipeline over the checkpoint.

    Uses `aggregation_strategy="simple"` so the pipeline returns entity-level
    spans with character offsets directly (`entity_group`, `start`, `end`) --
    matching this project's `Label` shape without extra BIOES decoding here.
    """
    from transformers import pipeline

    classifier = pipeline(
        "token-classification",
        model=str(checkpoint_dir),
        aggregation_strategy="simple",
        device=0 if device == "cuda" else -1,
    )
    predictions: dict[str, tuple[Label, ...]] = {}
    for document_id, text in text_by_document.items():
        entities = classifier(text)
        predictions[document_id] = tuple(
            Label(
                start=int(entity["start"]),
                end=int(entity["end"]),
                category=str(entity["entity_group"]),
            )
            for entity in entities
            if entity.get("start") is not None and entity.get("end") is not None
        )
    return predictions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the segmenter against the locked test set exactly once (§13/§16.2)"
    )
    parser.add_argument("--experiment-manifest", required=True)
    parser.add_argument("--data-dir", required=True, help="Dir containing the unlocked test.jsonl")
    parser.add_argument(
        "--dataset-release-id", required=True, help="segmenter-real-vX.Y this test belongs to"
    )
    parser.add_argument(
        "--model-release-id", required=True, help="segmenter-model-vX.Y being evaluated"
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--executor", required=True, help="Who/what unlocked the test (RFC 0012 §13.2)"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--device", default=None)
    parser.add_argument(
        "--i-understand-this-consumes-the-locked-test-set",
        action="store_true",
        help=(
            "Required. Confirms this run is THE single registered test evaluation for this "
            "model release (RFC 0012 §13.1) -- not a diagnostic re-check."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing model card at --output-dir. Refused by default.",
    )
    args = parser.parse_args(argv)

    if not args.i_understand_this_consumes_the_locked_test_set:
        print(
            "Refusing to run: pass --i-understand-this-consumes-the-locked-test-set to confirm "
            "this is THE single registered test evaluation for this model release (RFC 0012 "
            "§13.1). A second evaluation against the same holdout is a regression diagnostic, "
            "never a new performance claim.",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir)
    model_card_path = output_dir / "model_card.json"
    if model_card_path.exists() and not args.force:
        print(
            f"Refusing to overwrite existing model card at {model_card_path} without --force. "
            "A genuinely new evaluation (RFC 0012 §13.1's 'reação a teste' or 'novo candidato' "
            "trigger) belongs under a new --output-dir with its own holdout, not a second write "
            "here.",
            file=sys.stderr,
        )
        return 1

    experiment_manifest_path = Path(args.experiment_manifest)
    if not experiment_manifest_path.exists():
        print(f"Error: experiment manifest {experiment_manifest_path} not found.", file=sys.stderr)
        return 1
    experiment_manifest = ExperimentManifest.model_validate_json(
        experiment_manifest_path.read_text(encoding="utf-8")
    )

    test_jsonl = Path(args.data_dir) / "test.jsonl"
    if not test_jsonl.exists():
        print(f"Error: {test_jsonl} not found.", file=sys.stderr)
        return 1

    document_ids, gold_by_document, text_by_document = _load_test_jsonl(test_jsonl)
    device = args.device or _detect_device()

    unlocked_at = datetime.now(UTC)
    logger.info(
        "test_unlocked",
        executor=args.executor,
        at=unlocked_at.isoformat(),
        documents=len(document_ids),
    )

    model_predicted = _run_opf_inference(
        text_by_document, Path(experiment_manifest.checkpoint_dir), device
    )
    predictions = [
        DocumentModelPrediction(
            document_id=document_id,
            gold=gold_by_document[document_id],
            model_predicted=model_predicted.get(document_id, ()),
            baseline_predicted=(),
        )
        for document_id in document_ids
    ]

    evidence = evaluate_model_acceptance(predictions, seed=args.seed, resamples=args.resamples)
    result_hash = hashlib.sha256(evidence.model_dump_json().encode("utf-8")).hexdigest()

    tribunal_by_document, document_type_by_document = _load_document_groups(test_jsonl)

    model_card = ModelCard(
        release_id=args.model_release_id,
        dataset_release_id=args.dataset_release_id,
        experiment_id=experiment_manifest.experiment_id,
        test_release_used=args.dataset_release_id,
        test_unlocked_at=unlocked_at.isoformat(),
        test_unlocked_by=args.executor,
        test_result_hash=result_hash,
        acceptance=evidence,
        intended_use=(
            "TJRO acórdão segmentation into the RFC 0012 ontology regions; not validated on "
            "other tribunals or document types."
        ),
        known_limitations=(
            "Test-set support for critical categories is low (~30 documents); a point-estimate "
            "floor is used instead of a CI bound, per RFC 0012 §5 point 6.",
            "The baseline is majority-class (predicts no spans), per RFC 0012 §5 point 6's "
            "fallback -- no existing heuristic extractor was substituted in for this run.",
        ),
        created_at=unlocked_at.isoformat(),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    model_card_path.write_text(model_card.model_dump_json(indent=2) + "\n", encoding="utf-8")
    region_report_path = _write_region_report(predictions, output_dir)

    print(f"Model card: {model_card_path}")
    print(f"Region report: {region_report_path}")
    print(f"macro-F1 (model): {evidence.macro_f1_model}")
    print(f"macro-F1 (baseline): {evidence.macro_f1_baseline}")
    print(
        f"micro (model): precision={evidence.micro_precision_model} "
        f"recall={evidence.micro_recall_model} f1={evidence.micro_f1_model}"
    )
    print(f"baseline diff CI95 low: {evidence.baseline_diff_ci95_low}")
    print(f"beats baseline: {evidence.beats_baseline}")
    print(f"critical categories: {evidence.critical_category_f1}")
    print(f"critical categories passed: {evidence.critical_categories_passed}")
    _print_group_breakdown("tribunal", predictions, tribunal_by_document)
    _print_group_breakdown("document type", predictions, document_type_by_document)
    _print_region_group_breakdown("tribunal", predictions, tribunal_by_document)
    _print_region_group_breakdown("document type", predictions, document_type_by_document)
    print(f"ELIGIBLE FOR DEPLOY: {evidence.eligible_for_deploy}")
    return 0 if evidence.eligible_for_deploy else 2


if __name__ == "__main__":
    sys.exit(main())
