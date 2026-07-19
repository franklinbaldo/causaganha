from __future__ import annotations

import json

from scripts.run_segmenter_test_eval import _load_test_jsonl, main


def _write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")


def test_load_test_jsonl_reads_gold_labels_and_text(tmp_path):
    path = tmp_path / "test.jsonl"
    _write_jsonl(
        path,
        [
            {
                "text": "hello world",
                "label": [{"category": "resultado", "start": 0, "end": 5}],
                "info": {"document_id": "d1"},
            },
            {
                "text": "second doc",
                "label": [],
                "info": {"document_id": "d2"},
            },
        ],
    )

    document_ids, gold_by_document, text_by_document = _load_test_jsonl(path)

    assert document_ids == ["d1", "d2"]
    assert len(gold_by_document["d1"]) == 1
    assert gold_by_document["d1"][0].category == "resultado"
    assert gold_by_document["d2"] == ()
    assert text_by_document["d1"] == "hello world"


def test_load_test_jsonl_skips_blank_lines(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"text": "a", "label": [], "info": {"document_id": "d1"}}\n\n',
        encoding="utf-8",
    )

    document_ids, _gold, _text = _load_test_jsonl(path)

    assert document_ids == ["d1"]


def test_main_refuses_without_confirmation_flag(tmp_path, capsys):
    exit_code = main(
        [
            "--experiment-manifest",
            str(tmp_path / "missing.json"),
            "--data-dir",
            str(tmp_path),
            "--dataset-release-id",
            "segmenter-real-v8.1",
            "--model-release-id",
            "segmenter-model-v8.1",
            "--output-dir",
            str(tmp_path / "out"),
            "--executor",
            "test-runner",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "--i-understand-this-consumes-the-locked-test-set" in captured.err


def test_main_refuses_to_overwrite_existing_model_card_without_force(tmp_path, capsys):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "model_card.json").write_text("{}", encoding="utf-8")

    exit_code = main(
        [
            "--experiment-manifest",
            str(tmp_path / "missing.json"),
            "--data-dir",
            str(tmp_path),
            "--dataset-release-id",
            "segmenter-real-v8.1",
            "--model-release-id",
            "segmenter-model-v8.1",
            "--output-dir",
            str(output_dir),
            "--executor",
            "test-runner",
            "--i-understand-this-consumes-the-locked-test-set",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Refusing to overwrite" in captured.err


def test_main_errors_when_experiment_manifest_missing(tmp_path, capsys):
    exit_code = main(
        [
            "--experiment-manifest",
            str(tmp_path / "missing.json"),
            "--data-dir",
            str(tmp_path),
            "--dataset-release-id",
            "segmenter-real-v8.1",
            "--model-release-id",
            "segmenter-model-v8.1",
            "--output-dir",
            str(tmp_path / "out"),
            "--executor",
            "test-runner",
            "--i-understand-this-consumes-the-locked-test-set",
        ]
    )

    assert exit_code != 0
