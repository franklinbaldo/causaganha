"""Tests for scripts.run_staged_training — checkpoint-chained multi-stage orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scripts.run_staged_training import run_staged_training


def _config(tmp_path: Path, *, n_stages: int = 3) -> dict:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    stage_names = ["structural_broad", "adversarial_heavy", "real_finetune"][:n_stages]
    return {
        "run_id": "run_D_seed_3",
        "data_dir": str(data_dir),
        "output_dir": str(tmp_path / "out"),
        "device": "cpu",
        "stages": [
            {
                "name": name,
                "train_jsonl": str(tmp_path / f"{name}.jsonl"),
                "epochs": 1,
                "batch_size": 1,
            }
            for name in stage_names
        ],
    }


def _fake_result(train_rc: int = 0) -> dict:
    return {"train_rc": train_rc, "eval_rc": 0 if train_rc == 0 else None, "metrics": {}}


def test_first_stage_has_no_checkpoint(tmp_path: Path) -> None:
    config = _config(tmp_path, n_stages=1)
    with patch(
        "scripts.run_staged_training.train_and_eval", return_value=_fake_result()
    ) as mock_te:
        run_staged_training(config)

    assert mock_te.call_args.kwargs["checkpoint"] is None


def test_second_stage_chains_from_first_stage_checkpoint(tmp_path: Path) -> None:
    config = _config(tmp_path, n_stages=2)
    with patch(
        "scripts.run_staged_training.train_and_eval", return_value=_fake_result()
    ) as mock_te:
        run_staged_training(config)

    assert mock_te.call_count == 2
    first_call, second_call = mock_te.call_args_list
    assert first_call.kwargs["checkpoint"] is None
    expected_ckpt = Path(config["output_dir"]) / "structural_broad" / "best"
    assert second_call.kwargs["checkpoint"] == expected_ckpt


def test_stage_uses_its_own_train_jsonl_not_data_dir_default(tmp_path: Path) -> None:
    config = _config(tmp_path, n_stages=1)
    with patch(
        "scripts.run_staged_training.train_and_eval", return_value=_fake_result()
    ) as mock_te:
        run_staged_training(config)

    assert mock_te.call_args.kwargs["train_jsonl"] == Path(config["stages"][0]["train_jsonl"])


def test_aborts_chain_on_stage_failure(tmp_path: Path) -> None:
    config = _config(tmp_path, n_stages=3)
    with patch(
        "scripts.run_staged_training.train_and_eval",
        side_effect=[_fake_result(train_rc=0), _fake_result(train_rc=1)],
    ) as mock_te:
        report = run_staged_training(config)

    # Only 2 of 3 stages attempted: stage 2 failed, stage 3 never runs.
    assert mock_te.call_count == 2
    assert len(report["stages"]) == 2
    assert report["stages"][0]["train_rc"] == 0
    assert report["stages"][1]["train_rc"] == 1


def test_run_manifest_written_to_output_dir(tmp_path: Path) -> None:
    config = _config(tmp_path, n_stages=2)
    with patch("scripts.run_staged_training.train_and_eval", return_value=_fake_result()):
        run_staged_training(config)

    manifest_path = Path(config["output_dir"]) / "run_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run_D_seed_3"
    assert len(manifest["stages"]) == 2
    assert manifest["stages"][0]["name"] == "structural_broad"
    assert manifest["stages"][1]["checkpoint_from"] == str(
        Path(config["output_dir"]) / "structural_broad" / "best"
    )


def test_run_manifest_written_incrementally_even_on_failure(tmp_path: Path) -> None:
    """A partial manifest after a mid-chain failure is more useful than none —
    confirms the manifest reflects the attempted stage, not just successes.
    """
    config = _config(tmp_path, n_stages=2)
    with patch(
        "scripts.run_staged_training.train_and_eval",
        side_effect=[_fake_result(train_rc=1)],
    ):
        run_staged_training(config)

    manifest_path = Path(config["output_dir"]) / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["stages"]) == 1
    assert manifest["stages"][0]["train_rc"] == 1


def test_data_dir_shared_across_all_stages(tmp_path: Path) -> None:
    """val/test/label_space are never per-stage — only train_jsonl varies."""
    config = _config(tmp_path, n_stages=3)
    with patch(
        "scripts.run_staged_training.train_and_eval", return_value=_fake_result()
    ) as mock_te:
        run_staged_training(config)

    data_dirs = {call.args[0] for call in mock_te.call_args_list}
    assert data_dirs == {Path(config["data_dir"])}
