from __future__ import annotations

import json

import pytest

from scripts.run_segmenter_training import (
    _EpochResult,
    _load_label_space,
    _macro_f1_from_metrics,
    _select_best_epoch,
    main,
)


def test_load_label_space_requires_o_first(tmp_path):
    path = tmp_path / "label_space.json"
    path.write_text(json.dumps({"span_class_names": ["resultado", "O"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="O must be first"):
        _load_label_space(path)


def test_load_label_space_reads_valid_file(tmp_path):
    path = tmp_path / "label_space.json"
    payload = {"span_class_names": ["O", "resultado"], "category_version": "v8"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    label_space = _load_label_space(path)

    assert label_space["span_class_names"] == ["O", "resultado"]


def test_macro_f1_from_metrics_averages_by_class_keys():
    metrics = {"by_class.resultado.span.f1": 0.8, "by_class.dispositivo_abertura.span.f1": 0.6}

    macro = _macro_f1_from_metrics(metrics, ["resultado", "dispositivo_abertura"])

    assert macro == pytest.approx(0.7)


def test_macro_f1_from_metrics_falls_back_to_nested_f1_score():
    metrics = {"resultado": {"f1-score": 0.5}}

    macro = _macro_f1_from_metrics(metrics, ["resultado"])

    assert macro == pytest.approx(0.5)


def test_macro_f1_from_metrics_zero_when_no_category_found():
    assert _macro_f1_from_metrics({}, ["resultado"]) == 0.0


def test_select_best_epoch_picks_highest_macro_f1():
    results = [
        _EpochResult(epoch=1, macro_f1=0.5, val_loss=0.9, checkpoint_dir="epoch-1"),
        _EpochResult(epoch=2, macro_f1=0.8, val_loss=0.7, checkpoint_dir="epoch-2"),
        _EpochResult(epoch=3, macro_f1=0.6, val_loss=0.5, checkpoint_dir="epoch-3"),
    ]

    best = _select_best_epoch(results)

    assert best.epoch == 2


def test_select_best_epoch_ties_broken_by_lowest_epoch():
    results = [
        _EpochResult(epoch=1, macro_f1=0.8, val_loss=0.9, checkpoint_dir="epoch-1"),
        _EpochResult(epoch=2, macro_f1=0.8, val_loss=0.1, checkpoint_dir="epoch-2"),
    ]

    best = _select_best_epoch(results)

    assert best.epoch == 1


def test_select_best_epoch_falls_back_to_lowest_val_loss_on_full_tie():
    results = [
        _EpochResult(epoch=1, macro_f1=0.8, val_loss=0.9, checkpoint_dir="a"),
        _EpochResult(epoch=1, macro_f1=0.8, val_loss=0.2, checkpoint_dir="b"),
    ]

    best = _select_best_epoch(results)

    assert best.checkpoint_dir == "b"


def _main_args(tmp_path, **overrides: str):
    args = {
        "--data-dir": str(tmp_path),
        "--output-dir": str(tmp_path / "out"),
        "--release-id": "segmenter-real-v8.1",
        "--ontology-version": "segmenter-ontology-v8.0.0",
        "--guideline-version": "g1",
        "--dependency-lock-hash": "a" * 64,
    }
    args.update(overrides)
    flat = []
    for key, value in args.items():
        flat.extend([key, value])
    return flat


def test_main_errors_when_train_artifacts_are_missing(tmp_path, capsys):
    exit_code = main(_main_args(tmp_path))

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "missing" in captured.err
    assert "train.jsonl" in captured.err


def test_main_reports_all_missing_artifacts_not_just_the_first(tmp_path, capsys):
    (tmp_path / "train.jsonl").write_text("", encoding="utf-8")

    exit_code = main(_main_args(tmp_path))

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "val.jsonl" in captured.err
    assert "label_space.json" in captured.err
    assert "train.jsonl" not in captured.err
