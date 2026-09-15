"""Test the segmenter_dataset store governance status diagnostic (issue #1051).

``assign_splits`` (RFC 0012 §10) silently returns an empty val/test split
whenever the store has zero accepted :class:`ReviewRecord` objects — that is
correct behavior, not a bug (see ``EmptyEvalSplitError``'s docstring, which
only guards *starved* eligible groups, not a genuinely empty eligible set).
But nothing previously surfaced *that the store is in that state* without
someone running ``assign-splits`` by hand and reading stderr. This script
makes the gap a first-class, testable fact so future segmenter rounds don't
have to rediscover it.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from segmenter_dataset.schemas import (
    AnnotationRecord,
    AnnotatorConfig,
    DocumentRecord,
    ExtractionInfo,
    GroupingInfo,
    Label,
    ReviewRecord,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _write_document_and_annotation(store: SegmenterDatasetStore, doc_id: str, ann_id: str) -> None:
    store.write_document(
        DocumentRecord(
            document_id=doc_id,
            text="texto de exemplo",
            source=SourceInfo(
                system="sys1",
                tribunal="trib1",
                document_type="acordao",
                source_uri=f"uri-{doc_id}",
                source_hash=f"hash-{doc_id}",
            ),
            extraction=ExtractionInfo(method="method1", version="v1"),
            grouping=GroupingInfo(source_process_id=f"{doc_id}-process"),
        )
    )
    store.write_annotation(
        AnnotationRecord(
            annotation_id=ann_id,
            document_id=doc_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("resultado",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="resultado", start=0, end=1)],
        )
    )


def test_reports_zero_evaluation_eligible_when_store_has_no_reviews(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    _write_document_and_annotation(store, "doc_" + "1" * 32, "ann_" + "1" * 32)
    _write_document_and_annotation(store, "doc_" + "2" * 32, "ann_" + "2" * 32)

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    assert status["document_count"] == 2
    assert status["annotation_count"] == 2
    assert status["review_count"] == 0
    assert status["train_eligible_count"] == 2
    assert status["evaluation_eligible_count"] == 0
    assert status["blocked_on_reviews"] is True


def test_evaluation_eligible_count_reflects_accepted_reviews(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    doc_id = "doc_" + "3" * 32
    ann_id_1 = "ann_" + "3" * 32
    ann_id_2 = "ann_" + "4" * 32
    _write_document_and_annotation(store, doc_id, ann_id_1)
    store.write_annotation(
        AnnotationRecord(
            annotation_id=ann_id_2,
            document_id=doc_id,
            annotator_id="annotator2",
            annotator_config=AnnotatorConfig(
                model_family="other_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("resultado",),
            completed_at="2023-01-02T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="resultado", start=0, end=1)],
        )
    )
    store.write_review(
        ReviewRecord(
            review_id="rev_" + "5" * 32,
            document_id=doc_id,
            input_annotation_ids=(ann_id_1, ann_id_2),
            status="accepted",
            final_labels=[Label(category="resultado", start=0, end=1)],
            reviewers=("reviewer1", "reviewer2"),
            resolution="agreement",
            approved_at="2023-01-03T00:00:00Z",
        )
    )

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    assert status["review_count"] == 1
    assert status["evaluation_eligible_count"] == 1
    assert status["blocked_on_reviews"] is False


def test_real_store_has_zero_evaluation_eligible_documents() -> None:
    """Regression guard documenting the #1051 blocker's current, real state.

    As of this test's introduction, ``data/segmenter`` has 61 documents and
    74 annotations but zero ``ReviewRecord``s, so #1047's whole roadmap
    (which requires a real validation split, #1051) cannot be advanced by
    running ``assign-splits`` today -- it silently returns an empty val/test
    split (RFC 0012 §10: that role requires an *accepted* review, not just
    an annotation). This is a data/process gap, not a code bug: fixing it
    means adjudicating real reviews (#1051), not touching this diagnostic.
    If this test starts seeing ``blocked_on_reviews is False``, #1051 has
    made real progress -- update/remove this regression guard instead of
    treating a flip here as a failure.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["document_count"] > 0
    assert status["review_count"] == 0
    assert status["evaluation_eligible_count"] == 0
    assert status["blocked_on_reviews"] is True


def test_main_prints_json_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    _write_document_and_annotation(store, "doc_" + "6" * 32, "ann_" + "6" * 32)

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    mod.main(["--store", str(tmp_path / "store")])  # type: ignore[attr-defined]

    out = capsys.readouterr().out
    first_line_block = out.split("\n\n", 1)[0]
    payload = json.loads(first_line_block)
    assert payload["document_count"] == 1
    assert "WARNING" in out
