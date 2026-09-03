from __future__ import annotations

import json

import pytest

from scripts.run_segmenter_training import (
    _EpochResult,
    _load_label_space,
    _macro_f1_from_metrics,
    _run_opf_train_epoch,
    _select_best_epoch,
    _validation_loss_from_metrics,
    main,
)


def test_run_opf_train_epoch_uses_shuffle_seed_not_seed(tmp_path, monkeypatch):
    """`opf train`'s real CLI has no `--seed` flag (only `--shuffle-seed`) --
    confirmed against a real `opf train --help` on a GPU Kaggle kernel, which
    failed with "unrecognized arguments: --seed 42" before this fix. Locks in
    the fix since nothing else exercised the constructed subprocess command.
    """
    captured_cmd = {}

    class _FakeResult:
        returncode = 0

    def fake_run(cmd, *, check=False):
        del check
        captured_cmd["cmd"] = cmd
        return _FakeResult()

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    _run_opf_train_epoch(
        tmp_path / "train.jsonl",
        tmp_path / "val.jsonl",
        tmp_path / "label_space.json",
        tmp_path / "epoch-1",
        resume_from=None,
        batch_size=2,
        seed=42,
        device="cpu",
    )

    cmd = captured_cmd["cmd"]
    assert "--seed" not in cmd
    assert "--shuffle-seed" in cmd
    assert cmd[cmd.index("--shuffle-seed") + 1] == "42"


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


def test_macro_f1_from_metrics_reads_current_opf_envelope():
    metrics = {
        "args": {"eval_mode": "typed"},
        "metrics": {
            "by_class.resultado.span.f1": 0.8,
            "by_class.dispositivo_abertura.span.f1": 0.6,
            "loss": 0.9119997755866411,
        },
        "summary": {"examples": 3},
    }

    macro = _macro_f1_from_metrics(metrics, ["resultado", "dispositivo_abertura"])

    assert macro == pytest.approx(0.7)
    assert _validation_loss_from_metrics(metrics) == pytest.approx(0.9119997755866411)


def test_validation_loss_from_metrics_keeps_historical_flat_format():
    assert _validation_loss_from_metrics({"loss": 0.42}) == pytest.approx(0.42)


def test_validation_loss_from_metrics_none_when_missing():
    assert _validation_loss_from_metrics({"metrics": {}}) is None


def test_macro_f1_from_metrics_falls_back_to_nested_f1_score():
    metrics = {"resultado": {"f1-score": 0.5}}

    macro = _macro_f1_from_metrics(metrics, ["resultado"])

    assert macro == pytest.approx(0.5)


def test_macro_f1_from_metrics_zero_when_no_category_found():
    assert _macro_f1_from_metrics({}, ["resultado"]) == 0.0


def test_macro_f1_from_metrics_counts_missing_category_as_zero_not_excluded():
    """A trainable category absent from OPF's per-class report (e.g. zero
    predictions, or zero recall on a class OPF omits F1 for) must still count
    in the macro-F1 denominator as F1=0. Dropping it instead silently
    inflates macro-F1 by averaging only over the categories the model
    happened to report on (#1048).
    """
    metrics = {"by_class.resultado.span.f1": 0.8}

    macro = _macro_f1_from_metrics(metrics, ["resultado", "dispositivo_abertura"])

    assert macro == pytest.approx(0.4)


def test_macro_f1_from_metrics_counts_explicit_zero_recall_category():
    metrics = {"by_class.resultado.span.f1": 0.8, "by_class.dispositivo_abertura.span.f1": 0.0}

    macro = _macro_f1_from_metrics(metrics, ["resultado", "dispositivo_abertura"])

    assert macro == pytest.approx(0.4)


def test_macro_f1_from_metrics_denominator_is_stable_across_categories():
    """The denominator is always ``len(categories)``, never the count of
    categories OPF happened to report -- otherwise macro-F1 across two runs
    of the same categories is not comparable (#1048).
    """
    full_report = {
        "by_class.resultado.span.f1": 0.8,
        "by_class.dispositivo_abertura.span.f1": 0.6,
    }
    partial_report = {"by_class.resultado.span.f1": 0.8}

    categories = ["resultado", "dispositivo_abertura"]

    assert _macro_f1_from_metrics(full_report, categories) == pytest.approx(0.7)
    assert _macro_f1_from_metrics(partial_report, categories) == pytest.approx(0.4)


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
