#!/usr/bin/env python3
"""segment_decision.py — end-to-end inference for the v7 decision segmenter.

Chains the three pieces that were built separately but never wired together:

    1. OPF anchor-span prediction  (``opf predict`` subprocess, needs GPU)
    2. ref_normativa regex pre-pass + merge  (scripts/ref_normativa_prepass.py)
    3. Region reconstruction  (scripts/reconstruct_regions.py)

Input is JSONL with one ``{"text": ..., "info": {...}}`` record per line
(the same shape as the gold splits; an existing ``label`` field is ignored
unless ``--spans-from-label`` is set). Output is JSONL where each record
gains:

    "spans"   — final anchor spans (OPF + ref_normativa merged, no overlaps)
    "regions" — reconstructed regions [{category, start, end, matched}]

For development and testing without a GPU, ``--spans-from-label`` skips the
OPF call and uses each record's gold ``label`` as the model output. This
exercises the merge + reconstruction stages against real data — which is
exactly what the integration tests do.

Usage:
    # Full inference (needs trained checkpoint + GPU):
    uv run python scripts/segment_decision.py input.jsonl \
        --checkpoint models/decision_segmenter/best --output out.jsonl

    # GPU-less: run merge+reconstruction over gold spans:
    uv run python scripts/segment_decision.py data/segmenter_splits/test.jsonl \
        --spans-from-label --output out.jsonl
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

import structlog

from scripts.reconstruct_regions import reconstruct_regions, validate_anchor_lengths
from scripts.ref_normativa_prepass import extract_ref_normativa, merge_with_opf_spans


logger = structlog.get_logger()


def run_opf_predict(input_jsonl: Path, checkpoint: Path, device: str) -> list[list[dict]]:
    """Run ``opf predict`` and return one span list per input record.

    Mirrors the ``opf train`` / ``opf eval`` subprocess contract used by
    train_decision_segmenter.py: the output JSONL carries a ``label`` field
    with ``{category, start, end}`` spans per record.
    """
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
        out_path = Path(tmp.name)
    cmd = [
        sys.executable,
        "-m",
        "opf",
        "predict",
        str(input_jsonl),
        "--checkpoint",
        str(checkpoint),
        "--device",
        device,
        "--output",
        str(out_path),
    ]
    logger.info("opf_predict_start", cmd=" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        msg = f"opf predict failed with code {result.returncode}"
        raise RuntimeError(msg)
    predictions: list[list[dict]] = []
    with out_path.open(encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped:
                continue
            rec = json.loads(stripped)
            predictions.append(rec.get("label", []))
    out_path.unlink(missing_ok=True)
    return predictions


def segment_text(text: str, model_spans: list[dict]) -> dict:
    """Run the post-model pipeline: ref_normativa merge + region reconstruction.

    This is the pure, GPU-free core — model_spans can come from OPF or from
    gold labels. Returns {"spans": [...], "regions": [...], "warnings": [...]}.
    """
    ref_spans = extract_ref_normativa(text)
    merged = merge_with_opf_spans(model_spans, ref_spans)
    warnings = validate_anchor_lengths(merged, text)
    regions = reconstruct_regions(merged, len(text))
    return {
        "spans": merged,
        "regions": [asdict(r) for r in regions],
        "warnings": warnings,
    }


def _iter_records(path: Path):
    with path.open(encoding="utf-8") as fh:
        for ln, raw in enumerate(fh, 1):
            stripped = raw.strip()
            if not stripped:
                continue
            yield ln, json.loads(stripped)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", help="JSONL with {text, info} records")
    parser.add_argument("--output", help="Output JSONL path (default: stdout)")
    parser.add_argument("--checkpoint", help="OPF model checkpoint dir")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument(
        "--spans-from-label",
        action="store_true",
        help="Skip OPF; use each record's gold `label` as model spans (dev/test)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("input_not_found", path=str(input_path))
        return 1
    if not args.spans_from_label and not args.checkpoint:
        print(
            "Error: either --checkpoint (real inference) or "
            "--spans-from-label (dev mode) is required.",
            file=sys.stderr,
        )
        return 1

    records = list(_iter_records(input_path))

    if args.spans_from_label:
        predictions = [rec.get("label", []) for _, rec in records]
    else:
        predictions = run_opf_predict(input_path, Path(args.checkpoint), args.device)
        if len(predictions) != len(records):
            logger.error(
                "prediction_count_mismatch",
                records=len(records),
                predictions=len(predictions),
            )
            return 1

    n_regions = 0
    n_warnings = 0
    with contextlib.ExitStack() as stack:
        out_fh = (
            stack.enter_context(Path(args.output).open("w", encoding="utf-8"))
            if args.output
            else sys.stdout
        )
        for (ln, rec), model_spans in zip(records, predictions, strict=True):
            text = rec.get("text")
            if not isinstance(text, str):
                logger.error("missing_text", line=ln)
                continue
            result = segment_text(text, model_spans)
            n_regions += len(result["regions"])
            n_warnings += len(result["warnings"])
            for w in result["warnings"]:
                print(f"WARN L{ln}: {w}", file=sys.stderr)
            out = {
                "text": text,
                "spans": result["spans"],
                "regions": result["regions"],
            }
            if "info" in rec:
                out["info"] = rec["info"]
            out_fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    logger.info(
        "segmentation_done",
        records=len(records),
        regions=n_regions,
        warnings=n_warnings,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
