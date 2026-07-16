"""Tests for scripts.opf_shared — command construction and checkpoint chaining.

RFC 0011 §15-bis.3: ``run_staged_training.py`` (Runs B/D) needs
``train_and_eval``/``build_opf_train_cmd`` to accept a ``checkpoint``
directory and a per-stage ``train_jsonl`` override. These tests lock in
both the new behavior and the pre-existing default (no test file existed
for this module before).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.opf_shared import build_opf_train_cmd, train_and_eval


def test_build_opf_train_cmd_omits_checkpoint_by_default() -> None:
    cmd = build_opf_train_cmd(
        Path("train.jsonl"),
        Path("val.jsonl"),
        Path("label_space.json"),
        Path("out"),
        device="cpu",
        epochs=1,
        batch_size=1,
    )
    assert "--checkpoint" not in cmd


def test_build_opf_train_cmd_includes_checkpoint_when_given() -> None:
    cmd = build_opf_train_cmd(
        Path("train.jsonl"),
        Path("val.jsonl"),
        Path("label_space.json"),
        Path("out"),
        device="cpu",
        epochs=1,
        batch_size=1,
        checkpoint=Path("/models/stage1/best"),
    )
    idx = cmd.index("--checkpoint")
    assert cmd[idx + 1] == str(Path("/models/stage1/best"))


def test_train_and_eval_defaults_to_data_dir_train_jsonl(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with (
        patch("scripts.opf_shared.run_streamed", return_value=1) as mock_run,
        patch("scripts.opf_shared.build_opf_train_cmd", return_value=["fake"]) as mock_build,
    ):
        train_and_eval(data_dir, out_dir, device="cpu", epochs=1, batch_size=1, env={})

    mock_build.assert_called_once()
    call_kwargs = mock_build.call_args
    assert call_kwargs.args[0] == data_dir / "train.jsonl"
    assert mock_run.called


def test_train_and_eval_uses_train_jsonl_override(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    stage_mix = tmp_path / "stage1_mix" / "train.jsonl"

    with (
        patch("scripts.opf_shared.run_streamed", return_value=1),
        patch("scripts.opf_shared.build_opf_train_cmd", return_value=["fake"]) as mock_build,
    ):
        train_and_eval(
            data_dir,
            out_dir,
            device="cpu",
            epochs=1,
            batch_size=1,
            env={},
            train_jsonl=stage_mix,
        )

    assert mock_build.call_args.args[0] == stage_mix
    # val/test/label_space always come from data_dir, never the per-stage override.
    assert mock_build.call_args.args[1] == data_dir / "val.jsonl"
    assert mock_build.call_args.args[2] == data_dir / "label_space.json"


def test_train_and_eval_passes_checkpoint_through_to_build_cmd(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    prior_checkpoint = tmp_path / "stage1" / "best"

    with (
        patch("scripts.opf_shared.run_streamed", return_value=1),
        patch("scripts.opf_shared.build_opf_train_cmd", return_value=["fake"]) as mock_build,
    ):
        train_and_eval(
            data_dir,
            out_dir,
            device="cpu",
            epochs=1,
            batch_size=1,
            env={},
            checkpoint=prior_checkpoint,
        )

    assert mock_build.call_args.kwargs["checkpoint"] == prior_checkpoint


def test_train_and_eval_short_circuits_on_train_failure(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    with (
        patch("scripts.opf_shared.run_streamed", return_value=1) as mock_run,
        patch("scripts.opf_shared.build_opf_train_cmd", return_value=["fake"]),
    ):
        result = train_and_eval(data_dir, out_dir, device="cpu", epochs=1, batch_size=1, env={})

    assert result == {"train_rc": 1, "eval_rc": None, "metrics": None}
    # eval is never attempted after a failed train — only one run_streamed call.
    assert mock_run.call_count == 1
