#!/usr/bin/env python3
"""Staged/curriculum training orchestrator (RFC 0011 §15-bis.3, Runs B/D).

A single static mix (``compose_mix.py``) is enough for Runs C/E/F/G — one
``train.jsonl``, one ``opf train`` call, no driver changes. It is **not**
enough for Runs B (pretrain-on-synthetic then fine-tune-on-real) or D
(adversarial curriculum: broad-structural -> adversarial -> real-heavy):
those need multiple ``opf train`` calls in sequence, each continuing from
the previous stage's checkpoint via ``--checkpoint`` (verified supported
by opf itself, just not previously wired through
``opf_shared.build_opf_train_cmd``/``train_and_eval`` — see the
``checkpoint``/``train_jsonl`` parameters added there alongside this
script).

This script does **not** call ``compose_mix.py`` itself — mix composition
for each stage is the caller's responsibility, done ahead of time (e.g.
via ``scripts/synthetic_segmenter/compose_mix.py``, RFC 0011 §15-bis.3).
A stage config just points at an already-materialized ``train_jsonl`` per
stage. Keeping this orchestrator's own dependency footprint to
``opf_shared`` + stdlib means it composes with whatever produced those
files without needing to import them, and stays testable without a live
mix-generation dependency.

``val.jsonl``/``test.jsonl``/``label_space.json`` are never per-stage —
every stage reads the same ones from ``data_dir`` (RFC 0011 §12.1: val/
test never pass through mix composition, staged or not).

Stage config JSON shape::

    {
      "run_id": "run_D_seed_3",
      "data_dir": "data/segmenter_splits",
      "output_dir": "models/staged_run",
      "device": "cuda",
      "stages": [
        {"name": "structural_broad", "train_jsonl": "...", "epochs": 2, "batch_size": 4},
        {"name": "adversarial_heavy", "train_jsonl": "...", "epochs": 2, "batch_size": 4},
        {"name": "real_finetune", "train_jsonl": "data/segmenter_splits/train.jsonl",
         "epochs": 1, "batch_size": 2}
      ]
    }

Usage::

    uv run python scripts/run_staged_training.py --config staged_run.json

Aborts the chain (does not attempt later stages) if any stage's training
fails — chaining ``--checkpoint`` onto a stage that never produced one is
a corrupted-lineage bug, not something to paper over by skipping ahead.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

import structlog

from scripts.opf_shared import train_and_eval


logger = structlog.get_logger()


def run_staged_training(config: dict, *, env: dict | None = None) -> dict:
    """Run every stage in ``config["stages"]`` in order, chaining checkpoints.

    Returns the full run report: ``{"run_id", "stages": [...]}`` — one
    entry per stage attempted (a failed stage's entry is still included;
    stages after it are omitted, not attempted). Also written to
    ``output_dir/run_manifest.json`` for W&B/reproducibility lineage (RFC
    0011 §15-bis.3: "o manifest do mix ... é logado junto").
    """
    run_id = config["run_id"]
    data_dir = Path(config["data_dir"])
    output_dir = Path(config["output_dir"])
    device = config["device"]
    output_dir.mkdir(parents=True, exist_ok=True)

    run_env = dict(env if env is not None else os.environ)
    report: dict = {"run_id": run_id, "stages": []}
    previous_checkpoint: Path | None = None

    for stage in config["stages"]:
        stage_name = stage["name"]
        stage_out_dir = output_dir / stage_name
        stage_out_dir.mkdir(parents=True, exist_ok=True)
        train_jsonl = Path(stage["train_jsonl"])

        logger.info(
            "staged_training_stage_start",
            run_id=run_id,
            stage=stage_name,
            train_jsonl=str(train_jsonl),
            checkpoint_from=str(previous_checkpoint) if previous_checkpoint else None,
        )

        result = train_and_eval(
            data_dir,
            stage_out_dir,
            device=device,
            epochs=stage["epochs"],
            batch_size=stage["batch_size"],
            env=run_env,
            checkpoint=previous_checkpoint,
            train_jsonl=train_jsonl,
        )

        stage_report = {
            "name": stage_name,
            "train_jsonl": str(train_jsonl),
            "epochs": stage["epochs"],
            "batch_size": stage["batch_size"],
            "checkpoint_from": str(previous_checkpoint) if previous_checkpoint else None,
            "checkpoint_dir": str(stage_out_dir / "best"),
            **result,
        }
        report["stages"].append(stage_report)
        (output_dir / "run_manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        if result["train_rc"] != 0:
            logger.error(
                "staged_training_stage_failed",
                run_id=run_id,
                stage=stage_name,
                train_rc=result["train_rc"],
            )
            break

        logger.info(
            "staged_training_stage_complete",
            run_id=run_id,
            stage=stage_name,
            eval_rc=result["eval_rc"],
        )
        previous_checkpoint = stage_out_dir / "best"

    return report


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to the stage-config JSON file.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    report = run_staged_training(copy.deepcopy(config))

    failed = any(stage["train_rc"] != 0 for stage in report["stages"])
    attempted = len(report["stages"])
    total = len(config["stages"])
    if failed or attempted < total:
        logger.error(
            "staged_training_incomplete",
            run_id=report["run_id"],
            attempted=attempted,
            total=total,
        )
        return 1
    logger.info("staged_training_complete", run_id=report["run_id"], stages=attempted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
