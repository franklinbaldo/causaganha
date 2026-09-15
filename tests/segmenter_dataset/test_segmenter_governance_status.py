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


def test_real_store_has_at_least_one_evaluation_eligible_document() -> None:
    """Regression guard documenting #1051's first real, adjudicated review.

    Originally this test asserted ``review_count == 0`` /
    ``blocked_on_reviews is True`` — a snapshot of the store the day this
    diagnostic was introduced (61 documents, 74 annotations, zero
    ``ReviewRecord``s). That snapshot's own docstring already called for
    this update: "If this test starts seeing ``blocked_on_reviews is
    False``, #1051 has made real progress -- update/remove this regression
    guard instead of treating a flip here as a failure." It has: this store
    now carries the first accepted ``ReviewRecord``
    (``data/segmenter/reviews/doc_57d1c65ce480854290dc81fd59d4827d/``, built
    by ``scripts/adjudicate_segmenter_review.py`` from a second, genuinely
    independent annotation produced by ``scripts/annotate_second_independent.py``
    — see ``docs/planning/evidence/first-real-review-2026-09-15.json``), so
    ``assign-splits`` can produce a non-empty val/test manifest for the first
    time. #1051's remaining work is scaling this from 1 document to the
    RFC 0012 §5.4 targets (>= 30 val, >= 30 test adjudicated), not making the
    mechanism exist in the first place.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["document_count"] > 0
    assert status["review_count"] >= 1
    assert status["evaluation_eligible_count"] >= 1
    assert status["blocked_on_reviews"] is False


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
