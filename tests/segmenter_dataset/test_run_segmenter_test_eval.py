from __future__ import annotations

import json

from segmenter_dataset.model_eval import DocumentModelPrediction
from segmenter_dataset.schemas import Label
from scripts.run_segmenter_test_eval import (
    _load_document_groups,
    _load_test_jsonl,
    _write_region_report,
    main,
)


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


# #1052's "breakdown by tribunal/source and document type" checklist item:
# test.jsonl's info block already carries this metadata (opf_export.py's
# to_opf_record), so the eval script's own loader must expose it rather than
# discarding it like _load_test_jsonl does.


def test_load_document_groups_reads_tribunal_and_document_type(tmp_path):
    path = tmp_path / "test.jsonl"
    _write_jsonl(
        path,
        [
            {
                "text": "hello",
                "label": [],
                "info": {"document_id": "d1", "tribunal": "tjro", "document_type": "acordao"},
            },
            {
                "text": "world",
                "label": [],
                "info": {"document_id": "d2", "tribunal": "stj", "document_type": "acordao"},
            },
        ],
    )

    tribunal_by_document, document_type_by_document = _load_document_groups(path)

    assert tribunal_by_document == {"d1": "tjro", "d2": "stj"}
    assert document_type_by_document == {"d1": "acordao", "d2": "acordao"}


def test_load_document_groups_skips_documents_missing_the_metadata(tmp_path):
    path = tmp_path / "test.jsonl"
    _write_jsonl(
        path,
        [{"text": "a", "label": [], "info": {"document_id": "d1"}}],
    )

    tribunal_by_document, document_type_by_document = _load_document_groups(path)

    assert tribunal_by_document == {}
    assert document_type_by_document == {}


def test_load_document_groups_skips_blank_lines(tmp_path):
    path = tmp_path / "test.jsonl"
    path.write_text(
        '{"text": "a", "label": [], "info": {"document_id": "d1", "tribunal": "tjro"}}\n\n',
        encoding="utf-8",
    )

    tribunal_by_document, _document_type_by_document = _load_document_groups(path)

    assert tribunal_by_document == {"d1": "tjro"}


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


# #1052's region-level harness (segmenter_dataset.region_eval) is fully
# built and tested but was never wired into the script that produces the
# final model release evidence -- the locked-test evaluation only ever
# reported span-level metrics. This is the missing wiring.


def test_write_region_report_creates_file_with_region_metrics(tmp_path):
    predictions = [
        DocumentModelPrediction(
            document_id="d1",
            gold=(
                Label(start=0, end=10, category="relatorio_inicio"),
                Label(start=40, end=50, category="relatorio_fim"),
            ),
            model_predicted=(
                Label(start=0, end=10, category="relatorio_inicio"),
                Label(start=40, end=50, category="relatorio_fim"),
            ),
            baseline_predicted=(),
        )
    ]
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    report_path = _write_region_report(predictions, output_dir)

    assert report_path == output_dir / "region_report.txt"
    content = report_path.read_text(encoding="utf-8")
    assert "relatorio" in content
    assert "match_rate=1.000" in content


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
