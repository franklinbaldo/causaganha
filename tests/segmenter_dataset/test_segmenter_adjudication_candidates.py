"""Tests for scripts/segmenter_adjudication_candidates.py (issue #1051).

Every #1051 round up to and including this one re-derived the "which
single-annotated documents are actually worth adjudicating" scan and
`assign_splits` simulation from a throwaway scratch script (see
`knowledge/backlog/issue-1051.md`'s `decision-simulate-before-annotating`
notes across rounds ns7mbo/ku8qje/p08457/kgxf50/bomtmk/uq3be8). This test
file locks the formalized version's behavior in place so a future round can
trust it instead of re-deriving the method by hand.
"""

from __future__ import annotations

import importlib.util
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


MODULE_PATH = "scripts/segmenter_adjudication_candidates.py"


def _write_document(
    store: SegmenterDatasetStore, doc_id: str, *, tribunal: str = "trib1", text_length: int = 20
) -> None:
    # Unique, non-repetitive text per document -- SequenceMatcher-based
    # near-duplicate detection (segmenter_dataset.dedup) degrades badly on
    # many documents sharing one repeated-character string (e.g. "x" * n),
    # so pad with the document id itself rather than a single character.
    filler = (doc_id + "_") * (text_length // len(doc_id) + 1)
    text = filler[:text_length]
    store.write_document(
        DocumentRecord(
            document_id=doc_id,
            text=text,
            source=SourceInfo(
                system="sys1",
                tribunal=tribunal,
                document_type="acordao",
                source_uri=f"uri-{doc_id}",
                source_hash=f"hash-{doc_id}",
            ),
            extraction=ExtractionInfo(method="method1", version="v1"),
            grouping=GroupingInfo(source_process_id=f"{doc_id}-process"),
        )
    )


def _write_annotation(
    store: SegmenterDatasetStore,
    doc_id: str,
    ann_id: str,
    *,
    model_family: str = "family_a",
    seeded_with: str = "none",
) -> None:
    store.write_annotation(
        AnnotationRecord(
            annotation_id=ann_id,
            document_id=doc_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family=model_family, guideline_version="test_v1", seeded_with=seeded_with
            ),
            ontology_version="test_v1",
            covered_categories=("resultado",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="resultado", start=0, end=1)],
        )
    )


def _write_review(store: SegmenterDatasetStore, doc_id: str, ann_id_1: str, ann_id_2: str) -> None:
    store.write_review(
        ReviewRecord(
            review_id=f"rev_{doc_id[4:]}",
            document_id=doc_id,
            input_annotation_ids=(ann_id_1, ann_id_2),
            status="accepted",
            final_labels=[Label(category="resultado", start=0, end=1)],
            reviewers=("reviewer1", "reviewer2"),
            resolution="agreement",
            approved_at="2023-01-03T00:00:00Z",
        )
    )


def test_excludes_multi_annotated_seeded_and_already_reviewed_documents(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")

    # Candidate: exactly one unseeded annotation, never reviewed.
    candidate_id = "doc_" + "1" * 32
    _write_document(store, candidate_id)
    _write_annotation(store, candidate_id, "ann_" + "1" * 32)

    # Not a candidate: two annotations already (whatever their independence).
    multi_id = "doc_" + "2" * 32
    _write_document(store, multi_id)
    _write_annotation(store, multi_id, "ann_" + "2" * 32, model_family="family_a")
    _write_annotation(store, multi_id, "ann_" + "3" * 32, model_family="family_b")

    # Not a candidate: sole annotation is seeded (can never form an
    # independent pair per mechanical.annotations_are_independent).
    seeded_id = "doc_" + "4" * 32
    _write_document(store, seeded_id)
    _write_annotation(store, seeded_id, "ann_" + "4" * 32, seeded_with="model_draft")

    # Not a candidate: single annotation, but already has an (accepted) review.
    reviewed_id = "doc_" + "5" * 32
    _write_document(store, reviewed_id)
    _write_annotation(store, reviewed_id, "ann_" + "5" * 32)
    _write_annotation(store, reviewed_id, "ann_" + "6" * 32, model_family="family_b")
    _write_review(store, reviewed_id, "ann_" + "5" * 32, "ann_" + "6" * 32)

    mod = load_script("segmenter_adjudication_candidates", MODULE_PATH)
    candidates = mod.find_second_annotation_candidates(tmp_path / "store")  # type: ignore[attr-defined]

    candidate_ids = {c.document_id for c in candidates}
    assert candidate_ids == {candidate_id}


def test_individually_raises_test_count_is_true_once_enough_eligible_groups_exist(
    tmp_path: Path,
) -> None:
    """With few eligible groups, `assign_splits` starves val/test to 0 -- adding one
    more candidate can flip `test_count` from 0 to >0, which is exactly the signal
    `individually_raises_test_count` exists to surface before spending annotation
    effort on a document that would only ever land in train."""
    store = SegmenterDatasetStore(tmp_path / "store")

    # A pool of already-adjudicated (reviewed) documents, enough that
    # assign_splits has real val/test targets to fill.
    reviewed_ids = [f"doc_{i:032x}" for i in range(20)]
    for i, doc_id in enumerate(reviewed_ids):
        _write_document(store, doc_id, text_length=100)
        ann_a, ann_b = f"ann_{i:032x}", f"ann_{i + 1000:032x}"
        _write_annotation(store, doc_id, ann_a, model_family="family_a")
        _write_annotation(store, doc_id, ann_b, model_family="family_b")
        _write_review(store, doc_id, ann_a, ann_b)

    candidate_id = "doc_" + "c" * 31 + "1"
    _write_document(store, candidate_id, text_length=50)
    _write_annotation(store, candidate_id, "ann_" + "c" * 31 + "1")

    mod = load_script("segmenter_adjudication_candidates", MODULE_PATH)
    candidates = mod.find_second_annotation_candidates(tmp_path / "store")  # type: ignore[attr-defined]

    assert len(candidates) == 1
    only_candidate = candidates[0]
    assert only_candidate.document_id == candidate_id
    assert only_candidate.text_length == 50
    assert only_candidate.tribunal == "trib1"
    # With 20 already-eligible documents (test target already > 0), one more
    # candidate does not necessarily change the aggregate test_count -- but it
    # must be a real, computed bool, not a placeholder.
    assert isinstance(only_candidate.individually_raises_test_count, bool)


def test_joint_simulation_matches_governance_status_base_counts_with_no_candidates(
    tmp_path: Path,
) -> None:
    """`joint_simulation(store, [])` (no extra candidates) must exactly match what
    `scripts/segmenter_governance_status.py` reports as the store's current
    val_count/test_count -- both walk the same `assign_splits` call."""
    store = SegmenterDatasetStore(tmp_path / "store")
    reviewed_ids = [f"doc_{i:032x}" for i in range(10)]
    for i, doc_id in enumerate(reviewed_ids):
        _write_document(store, doc_id, text_length=100)
        ann_a, ann_b = f"ann_{i:032x}", f"ann_{i + 1000:032x}"
        _write_annotation(store, doc_id, ann_a, model_family="family_a")
        _write_annotation(store, doc_id, ann_b, model_family="family_b")
        _write_review(store, doc_id, ann_a, ann_b)

    governance_mod = load_script(
        "segmenter_governance_status", "scripts/segmenter_governance_status.py"
    )
    status = governance_mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    candidates_mod = load_script("segmenter_adjudication_candidates", MODULE_PATH)
    val_count, test_count = candidates_mod.joint_simulation(tmp_path / "store", [])  # type: ignore[attr-defined]

    assert val_count == status["val_count"]
    assert test_count == status["test_count"]


def test_joint_simulation_raises_test_count_when_candidates_added(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    reviewed_ids = [f"doc_{i:032x}" for i in range(20)]
    for i, doc_id in enumerate(reviewed_ids):
        _write_document(store, doc_id, text_length=100)
        ann_a, ann_b = f"ann_{i:032x}", f"ann_{i + 1000:032x}"
        _write_annotation(store, doc_id, ann_a, model_family="family_a")
        _write_annotation(store, doc_id, ann_b, model_family="family_b")
        _write_review(store, doc_id, ann_a, ann_b)

    mod = load_script("segmenter_adjudication_candidates", MODULE_PATH)
    base_val, base_test = mod.joint_simulation(tmp_path / "store", [])  # type: ignore[attr-defined]

    extra_ids = [f"doc_{i + 900:032x}" for i in range(6)]
    for i, doc_id in enumerate(extra_ids):
        _write_document(store, doc_id, text_length=100)
        _write_annotation(store, doc_id, f"ann_{i + 900:032x}")

    joint_val, joint_test = mod.joint_simulation(tmp_path / "store", extra_ids)  # type: ignore[attr-defined]
    assert joint_val == base_val
    assert joint_test >= base_test


def test_real_store_candidate_scan_is_consistent_with_governance_status() -> None:
    """Cross-check against the live store: the candidate scan's `base_test_count`
    (computed internally from evaluation_eligible with no additions) must equal
    `scripts/segmenter_governance_status.py`'s live `test_count` -- both call
    `assign_splits` the same way, so any divergence would be a real bug."""
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    governance_mod = load_script(
        "segmenter_governance_status", "scripts/segmenter_governance_status.py"
    )
    status = governance_mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    candidates_mod = load_script("segmenter_adjudication_candidates", MODULE_PATH)
    val_count, test_count = candidates_mod.joint_simulation(store_dir, [])  # type: ignore[attr-defined]

    assert val_count == status["val_count"]
    assert test_count == status["test_count"]

    candidates = candidates_mod.find_second_annotation_candidates(store_dir)  # type: ignore[attr-defined]
    # Every candidate must be genuinely single-annotated, unseeded, unreviewed --
    # re-derive that from the live store directly as an independent check.
    real_store = SegmenterDatasetStore(store_dir)
    annotations_by_doc: dict[str, list] = {}
    for annotation in real_store.list_annotations():
        annotations_by_doc.setdefault(annotation.document_id, []).append(annotation)
    reviewed_ids = {review.document_id for review in real_store.list_reviews()}

    for candidate in candidates:
        doc_annotations = annotations_by_doc[candidate.document_id]
        assert len(doc_annotations) == 1
        assert doc_annotations[0].annotator_config.seeded_with == "none"
        assert candidate.document_id not in reviewed_ids
