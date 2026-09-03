from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.run_segmenter_training import (
    _EpochResult,
    _detect_hardware,
    _detect_opf_version,
    _hash_dataset_export,
    _load_label_space,
    _macro_f1_from_metrics,
    _preserve_finetune_summary,
    _run_opf_train_epoch,
    _select_best_epoch,
    _validation_loss_from_metrics,
    main,
)
from segmenter_dataset.schemas import ExperimentManifest


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


# --- #1048: preserve OPF version, dataset export hash, hardware and
# finetune_summary.json in the experiment artifact -------------------------


def test_detect_opf_version_reads_stdout(monkeypatch):
    class _FakeResult:
        returncode = 0
        stdout = "opf 1.4.0\n"
        stderr = ""

    def fake_run(cmd, *, check, capture_output, text):
        del check, capture_output, text
        assert cmd[-1] == "--version"
        return _FakeResult()

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    assert _detect_opf_version() == "opf 1.4.0"


def test_detect_opf_version_none_when_opf_not_installed(monkeypatch):
    def fake_run(cmd, *, check, capture_output, text):
        del cmd, check, capture_output, text
        raise FileNotFoundError

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    assert _detect_opf_version() is None


def test_detect_opf_version_none_on_nonzero_returncode(monkeypatch):
    class _FakeResult:
        returncode = 1
        stdout = ""
        stderr = "unrecognized arguments: --version"

    monkeypatch.setattr(
        "scripts.run_segmenter_training.subprocess.run", lambda *a, **k: _FakeResult()
    )

    assert _detect_opf_version() is None


def test_detect_hardware_returns_device_for_cpu():
    assert _detect_hardware("cpu") == "cpu"


def test_detect_hardware_returns_gpu_name_for_cuda(monkeypatch):
    class _FakeCuda:
        @staticmethod
        def get_device_name(index):
            assert index == 0
            return "Tesla T4"

    class _FakeTorch:
        cuda = _FakeCuda()

    monkeypatch.setitem(__import__("sys").modules, "torch", _FakeTorch())

    assert _detect_hardware("cuda") == "Tesla T4"


def test_detect_hardware_falls_back_to_device_when_torch_unavailable(monkeypatch):
    """No torch installed in this test environment (confirmed in scripts/run_segmenter_training.py's
    own `_detect_device`, which already relies on this exact ImportError path) -- exercises the
    real fallback rather than a simulated one.
    """
    monkeypatch.delitem(__import__("sys").modules, "torch", raising=False)

    assert _detect_hardware("cuda") == "cuda"


def test_hash_dataset_export_is_deterministic_over_train_val_label_space(tmp_path):
    (tmp_path / "train.jsonl").write_text("a\n", encoding="utf-8")
    (tmp_path / "val.jsonl").write_text("b\n", encoding="utf-8")
    (tmp_path / "label_space.json").write_text('{"span_class_names": ["O"]}', encoding="utf-8")

    expected = hashlib.sha256()
    expected.update(b"a\n")
    expected.update(b"b\n")
    expected.update(b'{"span_class_names": ["O"]}')

    assert _hash_dataset_export(tmp_path) == expected.hexdigest()


def test_hash_dataset_export_changes_when_content_changes(tmp_path):
    (tmp_path / "train.jsonl").write_text("a\n", encoding="utf-8")
    (tmp_path / "val.jsonl").write_text("b\n", encoding="utf-8")
    (tmp_path / "label_space.json").write_text('{"span_class_names": ["O"]}', encoding="utf-8")
    before = _hash_dataset_export(tmp_path)

    (tmp_path / "train.jsonl").write_text("a-changed\n", encoding="utf-8")

    assert _hash_dataset_export(tmp_path) != before


def test_preserve_finetune_summary_copies_when_present(tmp_path):
    checkpoint_dir = tmp_path / "epoch-1"
    checkpoint_dir.mkdir()
    (checkpoint_dir / "finetune_summary.json").write_text('{"epochs": 1}', encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = _preserve_finetune_summary(checkpoint_dir, output_dir)

    assert result == str(output_dir / "finetune_summary.json")
    assert (output_dir / "finetune_summary.json").read_text(encoding="utf-8") == '{"epochs": 1}'


def test_preserve_finetune_summary_none_when_absent(tmp_path):
    checkpoint_dir = tmp_path / "epoch-1"
    checkpoint_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    result = _preserve_finetune_summary(checkpoint_dir, output_dir)

    assert result is None
    assert not (output_dir / "finetune_summary.json").exists()


def _write_train_artifacts(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "train.jsonl").write_text(
        json.dumps({"text": "t", "label": [], "info": {"document_id": "d1"}}) + "\n",
        encoding="utf-8",
    )
    (data_dir / "val.jsonl").write_text(
        json.dumps({"text": "v", "label": [], "info": {"document_id": "d2"}}) + "\n",
        encoding="utf-8",
    )
    (data_dir / "label_space.json").write_text(
        json.dumps({"span_class_names": ["O", "resultado"]}), encoding="utf-8"
    )


def test_main_writes_provenance_fields_into_experiment_manifest(tmp_path, monkeypatch, capsys):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)
    output_dir = tmp_path / "out"

    def fake_run(cmd, *, check=False, capture_output=False, text=False):
        del check
        if cmd[-1] == "--version":
            assert capture_output
            assert text

            class _VersionResult:
                returncode = 0
                stdout = "opf 9.9.9\n"
                stderr = ""

            return _VersionResult()

        if "train" in cmd:
            epoch_dir = Path(cmd[cmd.index("--output-dir") + 1])
            epoch_dir.mkdir(parents=True, exist_ok=True)
            (epoch_dir / "finetune_summary.json").write_text(
                '{"epochs": 1, "final_loss": 0.1}', encoding="utf-8"
            )

            class _TrainResult:
                returncode = 0

            return _TrainResult()

        if "eval" in cmd:
            metrics_out = Path(cmd[cmd.index("--metrics-out") + 1])
            metrics_out.write_text(
                json.dumps({"by_class.resultado.span.f1": 0.5, "loss": 0.2}), encoding="utf-8"
            )

            class _EvalResult:
                returncode = 0

            return _EvalResult()

        msg = f"unexpected command: {cmd}"
        raise AssertionError(msg)

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    exit_code = main(_main_args(tmp_path, **{"--data-dir": str(data_dir), "--epochs": "1"}))

    assert exit_code == 0
    manifest_path = output_dir / "experiment_manifest.json"
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    assert manifest.opf_version == "opf 9.9.9"
    assert manifest.hardware == "cpu"
    assert manifest.dataset_export_hash == _hash_dataset_export(data_dir)
    assert manifest.finetune_summary_path == str(output_dir / "finetune_summary.json")
    preserved = (output_dir / "finetune_summary.json").read_text(encoding="utf-8")
    assert json.loads(preserved) == {"epochs": 1, "final_loss": 0.1}
