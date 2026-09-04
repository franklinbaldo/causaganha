from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.run_segmenter_training import (
    DEFAULT_GRAD_ACCUM_STEPS,
    DEFAULT_LEARNING_RATE,
    DEFAULT_MAX_GRAD_NORM,
    DEFAULT_WEIGHT_DECAY,
    _detect_hardware,
    _detect_opf_version,
    _hash_dataset_export,
    _load_label_space,
    _macro_f1_from_metrics,
    _preserve_finetune_summary,
    _run_opf_train,
    _validation_loss_from_metrics,
    main,
    train_and_select_checkpoint,
)
from segmenter_dataset.schemas import ExperimentManifest


def test_run_opf_train_uses_shuffle_seed_not_seed(tmp_path, monkeypatch):
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

    _run_opf_train(
        tmp_path / "train.jsonl",
        tmp_path / "val.jsonl",
        tmp_path / "label_space.json",
        tmp_path / "checkpoint",
        epochs=3,
        batch_size=2,
        seed=42,
        device="cpu",
    )

    cmd = captured_cmd["cmd"]
    assert "--seed" not in cmd
    assert "--shuffle-seed" in cmd
    assert cmd[cmd.index("--shuffle-seed") + 1] == "42"


def test_run_opf_train_passes_full_epoch_count_in_one_call(tmp_path, monkeypatch):
    """#1048: one continuous `opf train --epochs N` call, not N one-epoch calls --
    re-invoking `opf train --epochs 1` per epoch resets OPF's optimizer/RNG
    state between calls, diverging from the canonical upstream semantics.
    """
    captured_cmd = {}

    class _FakeResult:
        returncode = 0

    def fake_run(cmd, *, check=False):
        del check
        captured_cmd["cmd"] = cmd
        return _FakeResult()

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    _run_opf_train(
        tmp_path / "train.jsonl",
        tmp_path / "val.jsonl",
        tmp_path / "label_space.json",
        tmp_path / "checkpoint",
        epochs=5,
        batch_size=2,
        seed=42,
        device="cpu",
    )

    cmd = captured_cmd["cmd"]
    assert cmd[cmd.index("--epochs") + 1] == "5"
    assert "--checkpoint" not in cmd


def test_default_optimization_recipe_matches_upstream_custom_label_demo():
    """#1048: the first serious baseline must start from the upstream
    custom-label harness defaults, not OPF's conservative built-in defaults
    (`lr=1e-5`, `wd=0.01` -- see docs/kaggle-colab-gpu-workflow.md). Without
    passing these flags explicitly, `opf train` silently uses the
    conservative recipe and diverges from the canonical baseline.
    """
    assert DEFAULT_LEARNING_RATE == pytest.approx(2e-4)
    assert DEFAULT_WEIGHT_DECAY == pytest.approx(0.0)
    assert DEFAULT_GRAD_ACCUM_STEPS == 1
    assert DEFAULT_MAX_GRAD_NORM == pytest.approx(1.0)


def test_run_opf_train_passes_optimization_recipe_flags(tmp_path, monkeypatch):
    """`opf train` must receive every optimization knob explicitly, so a run
    is reproducible from its recorded command rather than depending on
    whatever OPF's own internal defaults happen to be (#1048).
    """
    captured_cmd = {}

    class _FakeResult:
        returncode = 0

    def fake_run(cmd, *, check=False):
        del check
        captured_cmd["cmd"] = cmd
        return _FakeResult()

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    _run_opf_train(
        tmp_path / "train.jsonl",
        tmp_path / "val.jsonl",
        tmp_path / "label_space.json",
        tmp_path / "checkpoint",
        epochs=5,
        batch_size=2,
        seed=42,
        device="cpu",
        learning_rate=2e-4,
        weight_decay=0.0,
        grad_accum_steps=3,
        max_grad_norm=0.5,
    )

    cmd = captured_cmd["cmd"]
    assert cmd[cmd.index("--learning-rate") + 1] == "0.0002"
    assert cmd[cmd.index("--weight-decay") + 1] == "0.0"
    assert cmd[cmd.index("--grad-accum-steps") + 1] == "3"
    assert cmd[cmd.index("--max-grad-norm") + 1] == "0.5"


def test_run_opf_train_defaults_to_canonical_recipe_when_unspecified(tmp_path, monkeypatch):
    captured_cmd = {}

    class _FakeResult:
        returncode = 0

    def fake_run(cmd, *, check=False):
        del check
        captured_cmd["cmd"] = cmd
        return _FakeResult()

    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    _run_opf_train(
        tmp_path / "train.jsonl",
        tmp_path / "val.jsonl",
        tmp_path / "label_space.json",
        tmp_path / "checkpoint",
        epochs=5,
        batch_size=2,
        seed=42,
        device="cpu",
    )

    cmd = captured_cmd["cmd"]
    assert cmd[cmd.index("--learning-rate") + 1] == "0.0002"
    assert cmd[cmd.index("--weight-decay") + 1] == "0.0"
    assert cmd[cmd.index("--grad-accum-steps") + 1] == "1"
    assert cmd[cmd.index("--max-grad-norm") + 1] == "1.0"


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


def _fake_subprocess_run(*, train_metrics: dict | None = None, eval_metrics: dict | None = None):
    """Build a `subprocess.run` stand-in recording call count/cmds for `opf train`/`opf eval`."""
    calls: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def fake_run(cmd, *, check=False):
        del check
        calls.append(cmd)
        if "train" in cmd:
            output_dir = Path(cmd[cmd.index("--output-dir") + 1])
            output_dir.mkdir(parents=True, exist_ok=True)
            if train_metrics is not None:
                return _Result(1)
            return _Result(0)
        if "eval" in cmd:
            metrics_out = Path(cmd[cmd.index("--metrics-out") + 1])
            if eval_metrics is None:
                return _Result(1)
            metrics_out.parent.mkdir(parents=True, exist_ok=True)
            metrics_out.write_text(json.dumps(eval_metrics), encoding="utf-8")
            return _Result(0)
        msg = f"unexpected command: {cmd}"
        raise AssertionError(msg)

    return fake_run, calls


def test_train_and_select_checkpoint_invokes_opf_train_exactly_once(tmp_path, monkeypatch):
    """#1048: multi-epoch training is one `opf train --epochs N` call, never N calls."""
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)

    fake_run, calls = _fake_subprocess_run(eval_metrics={"by_class.resultado.span.f1": 0.7})
    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    train_and_select_checkpoint(
        data_dir, tmp_path / "out", epochs=5, batch_size=1, seed=0, device="cpu"
    )

    train_calls = [cmd for cmd in calls if "train" in cmd]
    assert len(train_calls) == 1
    assert train_calls[0][train_calls[0].index("--epochs") + 1] == "5"


def test_train_and_select_checkpoint_forwards_optimization_recipe(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)

    fake_run, calls = _fake_subprocess_run(eval_metrics={"by_class.resultado.span.f1": 0.7})
    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    train_and_select_checkpoint(
        data_dir,
        tmp_path / "out",
        epochs=5,
        batch_size=1,
        seed=0,
        device="cpu",
        learning_rate=1e-4,
        weight_decay=0.05,
        grad_accum_steps=2,
        max_grad_norm=2.0,
    )

    train_cmd = next(cmd for cmd in calls if "train" in cmd)
    assert train_cmd[train_cmd.index("--learning-rate") + 1] == "0.0001"
    assert train_cmd[train_cmd.index("--weight-decay") + 1] == "0.05"
    assert train_cmd[train_cmd.index("--grad-accum-steps") + 1] == "2"
    assert train_cmd[train_cmd.index("--max-grad-norm") + 1] == "2.0"


def test_train_and_select_checkpoint_returns_selection_from_final_eval(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)

    fake_run, _calls = _fake_subprocess_run(
        eval_metrics={"by_class.resultado.span.f1": 0.6, "loss": 0.3}
    )
    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    selection, checkpoint_dir = train_and_select_checkpoint(
        data_dir, tmp_path / "out", epochs=3, batch_size=1, seed=0, device="cpu"
    )

    assert selection.selected_epoch == 3
    assert selection.val_macro_f1 == pytest.approx(0.6)
    assert selection.val_loss == pytest.approx(0.3)
    assert checkpoint_dir == tmp_path / "out" / "checkpoint"


def test_train_and_select_checkpoint_raises_when_opf_train_fails(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)

    fake_run, _calls = _fake_subprocess_run(train_metrics={}, eval_metrics={})
    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="opf train failed"):
        train_and_select_checkpoint(
            data_dir, tmp_path / "out", epochs=1, batch_size=1, seed=0, device="cpu"
        )


def test_train_and_select_checkpoint_raises_when_opf_eval_fails(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)

    fake_run, _calls = _fake_subprocess_run(eval_metrics=None)
    monkeypatch.setattr("scripts.run_segmenter_training.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="opf eval"):
        train_and_select_checkpoint(
            data_dir, tmp_path / "out", epochs=1, batch_size=1, seed=0, device="cpu"
        )


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
    train_calls: list[list[str]] = []

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
            train_calls.append(cmd)
            checkpoint_dir = Path(cmd[cmd.index("--output-dir") + 1])
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            (checkpoint_dir / "finetune_summary.json").write_text(
                '{"epochs": 3, "final_loss": 0.1}', encoding="utf-8"
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

    exit_code = main(_main_args(tmp_path, **{"--data-dir": str(data_dir), "--epochs": "3"}))

    assert exit_code == 0
    # #1048: one continuous `opf train --epochs N` call, never N one-epoch calls.
    assert len(train_calls) == 1
    assert train_calls[0][train_calls[0].index("--epochs") + 1] == "3"
    manifest_path = output_dir / "experiment_manifest.json"
    manifest = ExperimentManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    assert manifest.opf_version == "opf 9.9.9"
    assert manifest.hardware == "cpu"
    assert manifest.dataset_export_hash == _hash_dataset_export(data_dir)
    assert manifest.finetune_summary_path == str(output_dir / "finetune_summary.json")
    preserved = (output_dir / "finetune_summary.json").read_text(encoding="utf-8")
    assert json.loads(preserved) == {"epochs": 3, "final_loss": 0.1}


def _fake_subprocess_run_for_main():
    """Same shape as `_fake_subprocess_run`, but also handles the `--version` probe main() runs."""

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
            checkpoint_dir = Path(cmd[cmd.index("--output-dir") + 1])
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

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

    return fake_run


def test_main_records_default_optimization_recipe_in_manifest(tmp_path, monkeypatch):
    """#1048: the recipe must be recorded even when the caller relies on the
    CLI defaults, so a manifest is reproducible on its own without assuming
    the reader knows this script's current default constants.
    """
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        "scripts.run_segmenter_training.subprocess.run", _fake_subprocess_run_for_main()
    )

    exit_code = main(_main_args(tmp_path, **{"--data-dir": str(data_dir)}))

    assert exit_code == 0
    manifest = ExperimentManifest.model_validate_json(
        (output_dir / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.learning_rate == pytest.approx(2e-4)
    assert manifest.weight_decay == pytest.approx(0.0)
    assert manifest.grad_accum_steps == 1
    assert manifest.max_grad_norm == pytest.approx(1.0)


def test_main_records_overridden_optimization_recipe_in_manifest(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    _write_train_artifacts(data_dir)
    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        "scripts.run_segmenter_training.subprocess.run", _fake_subprocess_run_for_main()
    )

    exit_code = main(
        _main_args(
            tmp_path,
            **{
                "--data-dir": str(data_dir),
                "--learning-rate": "1e-4",
                "--weight-decay": "0.05",
                "--grad-accum-steps": "4",
                "--max-grad-norm": "2.0",
            },
        )
    )

    assert exit_code == 0
    manifest = ExperimentManifest.model_validate_json(
        (output_dir / "experiment_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest.learning_rate == pytest.approx(1e-4)
    assert manifest.weight_decay == pytest.approx(0.05)
    assert manifest.grad_accum_steps == 4
    assert manifest.max_grad_norm == pytest.approx(2.0)
