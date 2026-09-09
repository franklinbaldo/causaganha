from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_annotation, make_document, make_review

from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import KnownLimitation, Label, ReviewRecord, SplitManifest
from segmenter_dataset.splits import SplitAssignment, SplitLeakError, create_split_manifest
from segmenter_dataset.store import SegmenterDatasetStore, _review_to_xml, _write_xml


CI_PROVIDER = "github-actions"
CI_RUN_ID = "run-1"


def _write_review_bypassing_independence_guard(
    store: SegmenterDatasetStore, review: ReviewRecord
) -> None:
    """Write a review straight to disk, skipping ``write_review``'s independence guard.

    Simulates a review that reached the store some other way than today's
    ``write_review`` (legacy data predating the guard, a direct XML edit) --
    used only to prove ``release.py``'s own ``_iaa_gates``/conflict-resolution
    checks still hold as defense-in-depth, independent of the store-level
    guard that now makes this state unreachable through the public API.
    """
    document_text = store.read_document(review.document_id).text
    path = store.reviews_dir / review.document_id / f"{review.review_id}.xml"
    _write_xml(path, _review_to_xml(review, document_text))


def _manifest_for(assignment: SplitAssignment) -> SplitManifest:
    return create_split_manifest(
        assignment,
        {},
        seed=1,
        train_ratio=0.7,
        val_ratio=0.15,
        near_duplicate_threshold=0.9,
    )


ONTOLOGY = {"cabecalho_inicio", "cabecalho_fim"}
PAIR_LABELS = [
    Label(start=0, end=5, category="cabecalho_inicio"),
    Label(start=10, end=15, category="cabecalho_fim"),
]
# Single-anchor category, non-overlapping with PAIR_LABELS' 10:15 span, used
# to add a third category to train/val only (never test) — see
# test_build_dataset_release_reports_per_category_support_across_splits.
RESULTADO_LABEL = Label(start=16, end=20, category="resultado")


def _text_for(role: str, index: int) -> str:
    # Unique per document — sharing text across documents would (correctly)
    # trip the cross-split content-hash leakage gate.
    return f"0123{role}{index:03d}89ABCDEFGHIJ"


# Both single-tribunal fixtures used by most tests below need this pair to
# pass the release (RFC 0012 §14's multiple_tribunals/multiple_source_systems
# advisory gates, wired for real — release.py's "advisory gate coverage"
# note).
SINGLE_TRIBUNAL_KNOWN_LIMITATIONS = [
    KnownLimitation(gate="multiple_tribunals", reason="TJRO-only for v8.1"),
    KnownLimitation(gate="multiple_source_systems", reason="tjro_juris-only for v8.1"),
]


def _labels_and_covered(extra_label: Label | None) -> tuple[list[Label], tuple[str, ...]]:
    labels = list(PAIR_LABELS)
    covered = ["cabecalho_inicio", "cabecalho_fim"]
    if extra_label is not None:
        labels.append(extra_label)
        covered.append(extra_label.category)
    return labels, tuple(covered)


def _seed_release(
    store: SegmenterDatasetStore,
    *,
    n_train: int,
    n_val: int,
    n_test: int,
    tribunals: tuple[str, ...] = ("TJRO",),
    extra_train_val_label: Label | None = None,
) -> SplitAssignment:
    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()

    train_labels, train_covered = _labels_and_covered(extra_train_val_label)
    for i in range(n_train):
        doc = make_document(
            text=_text_for("train", i),
            source_uri=f"train-{i}",
            tribunal=tribunals[i % len(tribunals)],
        )
        store.write_document(doc)
        annotation = make_annotation(doc, labels=train_labels, covered_categories=train_covered)
        store.write_annotation(annotation)
        train_ids.add(doc.document_id)

    for role, n, ids in (("val", n_val, val_ids), ("test", n_test, test_ids)):
        # extra_train_val_label applies to val (per its name) but not test —
        # deliberately, so a category can clear the train/val support floors
        # while remaining entirely unrepresented in the locked test split.
        role_labels, role_covered = _labels_and_covered(
            extra_train_val_label if role == "val" else None
        )
        for i in range(n):
            doc = make_document(text=_text_for(role, i), source_uri=f"{role}-{i}")
            store.write_document(doc)
            ann_a = make_annotation(
                doc,
                annotator_id="a",
                model_family="fam-a",
                labels=role_labels,
                covered_categories=role_covered,
            )
            ann_b = make_annotation(
                doc,
                annotator_id="b",
                model_family="fam-b",
                labels=role_labels,
                covered_categories=role_covered,
            )
            store.write_annotation(ann_a)
            store.write_annotation(ann_b)
            review = make_review(doc, [ann_a, ann_b], final_labels=role_labels)
            store.write_review(review)
            ids.add(doc.document_id)

    return SplitAssignment(
        train_ids=frozenset(train_ids), val_ids=frozenset(val_ids), test_ids=frozenset(test_ids)
    )


def test_build_dataset_release_succeeds_with_sufficient_support(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        ci_provider=CI_PROVIDER,
        ci_run_id=CI_RUN_ID,
        ontology_categories=ONTOLOGY,
        split_manifest=_manifest_for(assignment),
        known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
        iaa_seed=1,
    )

    assert manifest.counts == {"train": 10, "validation": 5, "test": 5}
    assert manifest.annotation_quality.val_iaa_span_f1 == 1.0
    assert manifest.annotation_quality.test_iaa_span_f1 == 1.0
    assert manifest.annotation_quality.unreliable_eval_categories == ()

    # RFC 0012 §12 step 9: refuses to overwrite an existing release.
    with pytest.raises(Exception, match="already exists"):
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(assignment),
            known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
            iaa_seed=1,
        )


def test_build_dataset_release_blocked_by_single_tribunal_without_known_limitation(
    tmp_path: Path,
) -> None:
    """Locks in that multiple_tribunals/multiple_source_systems are genuinely evaluated now.

    PR #838 review finding #3 — previously neither gate was ever computed,
    so a single-tribunal, single-source fixture like this one would build a
    release with no known_limitations at all.
    """
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(assignment),
            iaa_seed=1,
        )
    gate_names = {g.name for g in exc_info.value.gate_results}
    assert "multiple_tribunals" in gate_names
    assert "multiple_source_systems" in gate_names


def test_build_dataset_release_multiple_tribunals_gate_passes_without_waiver(
    tmp_path: Path,
) -> None:
    """A genuinely multi-tribunal corpus should not need a multiple_tribunals waiver.

    Only multiple_source_systems remains waived here (the fixture still uses
    a single source system).
    """
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5, tribunals=("TJRO", "TJSP"))

    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        ci_provider=CI_PROVIDER,
        ci_run_id=CI_RUN_ID,
        ontology_categories=ONTOLOGY,
        split_manifest=_manifest_for(assignment),
        known_limitations=[
            KnownLimitation(gate="multiple_source_systems", reason="tjro_juris-only for v8.1")
        ],
        iaa_seed=1,
    )
    assert manifest.tribunals.keys() == {"TJRO", "TJSP"}
    assert manifest.known_limitations[0].gate == "multiple_source_systems"


def test_build_dataset_release_blocked_by_insufficient_train_support(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=2, n_val=5, n_test=5)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(assignment),
            iaa_seed=1,
        )
    gate_names = {g.name for g in exc_info.value.gate_results}
    assert "train_minimum_support_per_category" in gate_names


def test_build_dataset_release_raises_when_val_document_not_adjudicated(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    # Add one more document with only an annotation (no review) but assign
    # it to val — a document that hasn't reached the role's required state.
    unreviewed = make_document(text="0123456789ABCDEFGHIJ", source_uri="val-unreviewed")
    store.write_document(unreviewed)
    store.write_annotation(
        make_annotation(
            unreviewed,
            labels=PAIR_LABELS,
            covered_categories=("cabecalho_inicio", "cabecalho_fim"),
        )
    )
    broken_assignment = SplitAssignment(
        train_ids=assignment.train_ids,
        val_ids=assignment.val_ids | {unreviewed.document_id},
        test_ids=assignment.test_ids,
    )

    with pytest.raises(SplitLeakError, match="no accepted review record"):
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(broken_assignment),
            iaa_seed=1,
        )


def test_build_dataset_release_advisory_gate_waived_by_known_limitation(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    # multiple_tribunals and multiple_source_systems are both genuinely
    # evaluated as failing for this single-tribunal, single-source fixture
    # (PR #838 review finding #3) — both need a matching known_limitation or
    # the release is blocked (see the sibling "blocked_by_single_tribunal"
    # test above for the unwaived case).
    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.2",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        ci_provider=CI_PROVIDER,
        ci_run_id=CI_RUN_ID,
        ontology_categories=ONTOLOGY,
        split_manifest=_manifest_for(assignment),
        known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
        iaa_seed=1,
    )
    waived_gates = {kl.gate for kl in manifest.known_limitations}
    assert waived_gates == {"multiple_tribunals", "multiple_source_systems"}


def test_build_dataset_release_reports_per_category_support_across_splits(tmp_path: Path) -> None:
    """category_counts surfaces per-split, per-category support (#1050/#1051).

    A category can clear both the train and val support floors (RFC 0012
    §5.4) while remaining completely unrepresented in the locked test split
    -- no gate checks test support today, so that blind spot would otherwise
    stay invisible until model evaluation runs. The report must make it
    visible as an explicit zero.
    """
    store = SegmenterDatasetStore(tmp_path)
    ontology = ONTOLOGY | {"resultado"}
    assignment = _seed_release(
        store, n_train=10, n_val=5, n_test=5, extra_train_val_label=RESULTADO_LABEL
    )

    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        ci_provider=CI_PROVIDER,
        ci_run_id=CI_RUN_ID,
        ontology_categories=ontology,
        split_manifest=_manifest_for(assignment),
        known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
        iaa_seed=1,
    )

    assert manifest.category_counts["train:cabecalho_inicio"] == 10
    assert manifest.category_counts["val:cabecalho_inicio"] == 5
    assert manifest.category_counts["test:cabecalho_inicio"] == 5
    assert manifest.category_counts["train:resultado"] == 10
    assert manifest.category_counts["val:resultado"] == 5
    # never annotated in the locked test split -- must be reported as an
    # explicit zero, not silently absent from the report.
    assert manifest.category_counts["test:resultado"] == 0


def test_build_dataset_release_blocked_by_unresolved_annotation_conflict(tmp_path: Path) -> None:
    """RFC 0012 §14: 'nenhum conflito de anotação não resolvido' is a rigid gate.

    A train document with two annotation records whose labels disagree, and
    no accepted review naming both annotation_ids, is an unresolved conflict
    -- distinct from val_test_independently_adjudicated (which only checks
    that val/test documents *have* an accepted review at all, never that a
    disagreement elsewhere was actually adjudicated). Before this gate is
    wired to real evidence, ``resolve_split``'s "latest annotation wins" for
    train silently picks one side of the disagreement with zero record that
    the other annotator's conflicting labels were ever looked at.
    """
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    conflicted = make_document(text="0123conflict00089ABCDEFGHIJ", source_uri="train-conflict")
    store.write_document(conflicted)
    ann_a = make_annotation(
        conflicted,
        annotator_id="a",
        model_family="family-a",
        completed_at="2026-01-01T00:00:00Z",
        labels=PAIR_LABELS,
        covered_categories=("cabecalho_inicio", "cabecalho_fim"),
    )
    ann_b = make_annotation(
        conflicted,
        annotator_id="b",
        model_family="family-b",
        completed_at="2026-01-02T00:00:00Z",
        labels=[
            Label(start=0, end=5, category="cabecalho_inicio"),
            Label(start=12, end=15, category="cabecalho_fim"),
        ],
        covered_categories=("cabecalho_inicio", "cabecalho_fim"),
    )
    store.write_annotation(ann_a)
    store.write_annotation(ann_b)
    broken_assignment = SplitAssignment(
        train_ids=assignment.train_ids | {conflicted.document_id},
        val_ids=assignment.val_ids,
        test_ids=assignment.test_ids,
    )

    with pytest.raises(ReleaseBlockedError) as exc_info:
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(broken_assignment),
            known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
            iaa_seed=1,
        )
    gate_names = {g.name for g in exc_info.value.gate_results}
    assert "no_unresolved_annotation_conflicts" in gate_names

    # Once an accepted review names both disagreeing annotation_ids, the
    # conflict is resolved and the gate passes.
    review = make_review(conflicted, [ann_a, ann_b], final_labels=ann_a.labels)
    store.write_review(review)
    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.2",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        ci_provider=CI_PROVIDER,
        ci_run_id=CI_RUN_ID,
        ontology_categories=ONTOLOGY,
        split_manifest=_manifest_for(broken_assignment),
        known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
        iaa_seed=1,
    )
    assert manifest.counts["train"] == 11


def test_build_dataset_release_blocked_when_val_pairs_are_not_independent(
    tmp_path: Path,
) -> None:
    """RFC 0012 §5.3: a review built from a copied/seeded annotation pair must
    never certify IAA.

    Each val document below is "adjudicated" from two annotations where the
    second is explicitly seeded with the first's own annotation_id (e.g. a
    correction pass over a model draft, RFC 0012 §9's own example of what is
    *not* independent) and simply repeats its labels. ``write_review`` itself
    now refuses to persist such a pair as ``accepted``
    (``NonIndependentReviewError``), so these are written straight to disk
    via ``_write_review_bypassing_independence_guard`` to simulate a review
    that reached the store some other way (legacy data, a direct XML edit) --
    proving ``_iaa_gates`` still excludes it from IAA and blocks the release
    as defense-in-depth, not merely relying on the store-level guard.
    """
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=0, n_test=5)

    val_ids: set[str] = set()
    role_labels, role_covered = _labels_and_covered(None)
    for i in range(5):
        doc = make_document(text=_text_for("val", i), source_uri=f"val-{i}")
        store.write_document(doc)
        ann_a = make_annotation(
            doc,
            annotator_id="a",
            model_family="fam-a",
            labels=role_labels,
            covered_categories=role_covered,
        )
        # Seeded from ann_a and left otherwise identical -- a correction pass
        # over a model draft, not a second independent annotator.
        ann_b = make_annotation(
            doc,
            annotator_id="b",
            model_family="fam-a",
            seeded_with=ann_a.annotation_id,
            labels=role_labels,
            covered_categories=role_covered,
        )
        store.write_annotation(ann_a)
        store.write_annotation(ann_b)
        review = make_review(doc, [ann_a, ann_b], final_labels=role_labels)
        _write_review_bypassing_independence_guard(store, review)
        val_ids.add(doc.document_id)

    assignment = SplitAssignment(
        train_ids=assignment.train_ids,
        val_ids=frozenset(val_ids),
        test_ids=assignment.test_ids,
    )

    with pytest.raises(ReleaseBlockedError) as exc_info:
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="a" * 40,
            dependency_lock_hash="b" * 64,
            ci_provider=CI_PROVIDER,
            ci_run_id=CI_RUN_ID,
            ontology_categories=ONTOLOGY,
            split_manifest=_manifest_for(assignment),
            known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
            iaa_seed=1,
        )
    gate_names = {g.name for g in exc_info.value.gate_results}
    assert "iaa_aggregate_floor" in gate_names
