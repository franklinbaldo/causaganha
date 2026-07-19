"""Test segmenter audit scripts."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from segmenter_dataset.schemas import (
    AnnotationRecord,
    AnnotatorConfig,
    DocumentRecord,
    ExtractionInfo,
    GroupingInfo,
    Label,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def setup_dummy_store(tmp_path: Path) -> SegmenterDatasetStore:
    store = SegmenterDatasetStore(tmp_path / "store")

    document = DocumentRecord(
        document_id="doc_00000000000000000000000000000001",
        text="A B C D E F art. 1 art. 2 R$ 1 R$ 2 R$ 3 art. 3 art. 4",
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="acordao",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(document)

    annotator_config = AnnotatorConfig(
        model_family="test_model",
        guideline_version="test_v1",
    )
    annotation = AnnotationRecord(
        annotation_id="ann_00000000000000000000000000000001",
        document_id="doc_00000000000000000000000000000001",
        annotator_id="annotator1",
        annotator_config=annotator_config,
        ontology_version="test_v1",
        covered_categories=(
            "resultado",
            "relatorio_inicio",
            "relatorio_fim",
            "fundamentacao_legal",
        ),
        completed_at="2023-01-01T00:00:00Z",
        annotation_method="method1",
        labels=[
            Label(category="resultado", start=0, end=1),
            Label(category="relatorio_inicio", start=2, end=3),
            Label(category="relatorio_fim", start=4, end=5),
            Label(category="fundamentacao_legal", start=12, end=18),
        ],
    )
    store.write_annotation(annotation)
    return store


def test_compute_support(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    label_space_path = tmp_path / "label_space.json"
    label_space_path.write_text(
        json.dumps(
            {
                "span_class_names": [
                    "O",
                    "resultado",
                    "relatorio_inicio",
                    "relatorio_fim",
                    "fundamentacao_legal",
                ]
            }
        )
    )

    mod = load_script("segmenter_category_support", "scripts/segmenter_category_support.py")
    counts = mod.compute_support(tmp_path / "store", label_space_path)  # type: ignore[attr-defined]

    assert counts["resultado"] == 1
    assert counts["relatorio_inicio"] == 1
    assert counts["relatorio_fim"] == 1
    assert counts["fundamentacao_legal"] == 1


def test_compute_gaps(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    mod = load_script("segmenter_coverage_gap", "scripts/segmenter_coverage_gap.py")
    gaps = mod.compute_gaps(tmp_path / "store")  # type: ignore[attr-defined]

    bucket_key = "sys1|method1|annotator1"
    assert bucket_key in gaps
    assert gaps[bucket_key] == []


def test_find_anti_patterns(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    doc_id = "doc_00000000000000000000000000000001"
    assert doc_id in findings
    assert any(f["type"] == "fundamentacao_legal_collapsed" for f in findings[doc_id])
