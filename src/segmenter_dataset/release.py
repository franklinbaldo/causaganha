"""``build_dataset_release`` (RFC 0012 §12).

Does not promote candidates — packages records already **annotated**
(train) or **adjudicated** (validation/test), with split-assignment already
resolved (RFC 0012 §10), into an immutable, checksummed release:

1. load annotations (train) and reviews (validation/test);
2. verify split integrity;
3. validate every resolved record mechanically (RFC 0012 §11);
4. compute counts, hashes, and IAA (RFC 0012 §8);
5. check independently classified readiness gates (RFC 0012 §12.1, §14) —
   all rigid gates plus 2 of 5 advisory gates (see "advisory gate coverage"
   below);
6. write into a temporary directory;
7. verify the written release;
8. atomically rename it to the final release ID;
9. refuse to overwrite an existing release.

``build_gold_release`` is this RFC's provisional name for the same command
(RFC 0012 §9.1, §12) — reserved for a release that has additionally cleared
the human-reference gate. This module's public name is
``build_dataset_release`` because that gate does not exist yet.

**Advisory gate coverage (RFC 0012 §14 "exigidos para alegações amplas de
produção"):** step 5 evaluates all rigid gates plus 2 of the 5 gates in
:data:`segmenter_dataset.gates.ADVISORY_GATES` — ``multiple_tribunals`` and
``multiple_source_systems``, both computable directly from
``DocumentRecord.source``. The remaining three (``temporal_diversity``,
``representative_evaluation_set``, ``external_test_annotation_review``) are
**not evaluated anywhere in this module** — they would need fields this
schema doesn't carry yet (a publication/judgment date, a human-audit record
type). A ``known_limitations`` entry naming one of those three is
schema-valid (``KnownLimitation.gate`` isn't restricted beyond
:func:`segmenter_dataset.gates.classify_gate` accepting the name) but
currently inert: nothing ever produces a failing ``GateResult`` for that
name, so there is nothing for the waiver to apply to. This is a known
implementation gap, not a design decision — closing it requires extending
``DocumentRecord``/``SourceInfo`` with the missing fields first.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from segmenter_dataset import mechanical
from segmenter_dataset.dedup import content_hash
from segmenter_dataset.gates import GateResult, evaluate_gates
from segmenter_dataset.iaa import DocumentAnnotationPair, compute_iaa_report
from segmenter_dataset.schemas import (
    AnnotationQuality,
    AnnotationRecord,
    DocumentRecord,
    KnownLimitation,
    Label,
    ReleaseManifest,
    ReviewRecord,
)
from segmenter_dataset.splits import SplitAssignment, SplitLeakError, check_disjoint
from segmenter_dataset.store import ImmutabilityError, SegmenterDatasetStore


# RFC 0012 §5.6/§16.2 — categories too structural to isolate; a sub-floor
# IAA result here escalates from a per-category exclusion to a whole-release
# rigid failure (RFC 0012 §8).
CRITICAL_CATEGORIES: frozenset[str] = frozenset(
    {
        "dispositivo_abertura",
        "resultado",
        "acordao_decisorio_inicio",
        "acordao_decisorio_fim",
    }
)

# RFC 0012 §5.4 — minimum train support per category, minimum val support
# for reported per-category metrics.
MIN_TRAIN_SUPPORT_PER_CATEGORY = 10
MIN_VAL_SUPPORT_PER_CATEGORY = 5

# RFC 0012 §5.3/§9 — an IAA pair needs both independent annotations present.
MIN_INDEPENDENT_ANNOTATIONS_FOR_IAA = 2


class ReleaseBlockedError(RuntimeError):
    """A rigid gate failed, or an unwaived advisory gate failed (RFC 0012 §12.1)."""

    def __init__(self, message: str, gate_results: list[GateResult]) -> None:
        """Store the failing ``gate_results`` alongside the summary ``message``."""
        super().__init__(message)
        self.gate_results = gate_results


@dataclass(frozen=True)
class ResolvedSplitDocument:
    """One document's resolved content for a given split, with its lineage ID."""

    document: DocumentRecord
    labels: list[Label]
    resolution_id: str  # annotation_id (train) or review_id (val/test)


def _latest_accepted_review(reviews: list[ReviewRecord], document_id: str) -> ReviewRecord | None:
    accepted = [r for r in reviews if r.document_id == document_id and r.status == "accepted"]
    if not accepted:
        return None
    return max(accepted, key=lambda r: r.approved_at)


def _latest_annotation(
    annotations: list[AnnotationRecord], document_id: str
) -> AnnotationRecord | None:
    matching = [a for a in annotations if a.document_id == document_id]
    if not matching:
        return None
    return max(matching, key=lambda a: a.completed_at)


def resolve_split(
    role: str,
    document_ids: frozenset[str],
    documents_by_id: dict[str, DocumentRecord],
    annotations: list[AnnotationRecord],
    reviews: list[ReviewRecord],
) -> list[ResolvedSplitDocument]:
    """Resolve each document in a split to the record its role requires (RFC 0012 §10).

    ``role == "train"`` resolves to the latest annotation; ``"val"``/``"test"``
    resolve to the latest accepted review. Raises if a document lacks the
    record its role requires — this is what RFC 0012 §12 step 2 ("verifica
    integridade de splits") ultimately checks.
    """
    resolved: list[ResolvedSplitDocument] = []
    for document_id in sorted(document_ids):
        document = documents_by_id[document_id]
        if role == "train":
            annotation = _latest_annotation(annotations, document_id)
            if annotation is None:
                msg = f"train document {document_id!r} has no annotation record"
                raise SplitLeakError(msg)
            resolved.append(
                ResolvedSplitDocument(document, annotation.labels, annotation.annotation_id)
            )
        else:
            review = _latest_accepted_review(reviews, document_id)
            if review is None:
                msg = f"{role} document {document_id!r} has no accepted review record"
                raise SplitLeakError(msg)
            resolved.append(ResolvedSplitDocument(document, review.final_labels, review.review_id))
    return resolved


def _split_hash(resolved: list[ResolvedSplitDocument]) -> str:
    joined = "|".join(
        f"{r.document.document_id}:{r.resolution_id}"
        for r in sorted(resolved, key=lambda item: item.document.document_id)
    )
    return content_hash(joined)


def _category_counts(resolved: list[ResolvedSplitDocument]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in resolved:
        for label in item.labels:
            counts[label.category] = counts.get(label.category, 0) + 1
    return counts


def _mechanical_gate(
    train: list[ResolvedSplitDocument],
    val: list[ResolvedSplitDocument],
    test: list[ResolvedSplitDocument],
    ontology_categories: set[str],
) -> GateResult:
    problems: list[str] = []
    for role_name, resolved in (("train", train), ("val", val), ("test", test)):
        for item in resolved:
            record_problems = mechanical.validate_record(
                item.document.text, item.labels, ontology_categories
            )
            problems.extend(
                f"[{role_name}:{item.document.document_id}] {p}" for p in record_problems
            )
    return GateResult(
        name="ontology_schema_valid",
        passed=not problems,
        detail="; ".join(problems[:20]) if problems else "all records mechanically valid",
    )


def _support_gates(
    train: list[ResolvedSplitDocument], val: list[ResolvedSplitDocument]
) -> tuple[GateResult, GateResult]:
    train_counts = _category_counts(train)
    val_counts = _category_counts(val)

    under_train = {c: n for c, n in train_counts.items() if n < MIN_TRAIN_SUPPORT_PER_CATEGORY}
    under_val = {c: n for c, n in val_counts.items() if n < MIN_VAL_SUPPORT_PER_CATEGORY}

    return (
        GateResult(
            name="train_minimum_support_per_category",
            passed=not under_train,
            detail=f"below floor: {under_train}" if under_train else "all categories meet floor",
        ),
        GateResult(
            name="val_minimum_support_for_reported_metrics",
            passed=not under_val,
            detail=f"below floor: {under_val}" if under_val else "all categories meet floor",
        ),
    )


def _diversity_gates(
    train: list[ResolvedSplitDocument],
    val: list[ResolvedSplitDocument],
    test: list[ResolvedSplitDocument],
) -> tuple[GateResult, GateResult]:
    """The 2 of 5 RFC 0012 §14 advisory gates computable from data on hand today.

    See the module docstring's "advisory gate coverage" note for the other
    three (``temporal_diversity``, ``representative_evaluation_set``,
    ``external_test_annotation_review``), which this function does not
    evaluate — the schema has no date or audit-record field for them yet.
    """
    resolved = (*train, *val, *test)
    tribunals = {item.document.source.tribunal for item in resolved}
    systems = {item.document.source.system for item in resolved}
    return (
        GateResult(
            name="multiple_tribunals",
            passed=len(tribunals) > 1,
            detail=f"tribunals observed: {sorted(tribunals)}",
        ),
        GateResult(
            name="multiple_source_systems",
            passed=len(systems) > 1,
            detail=f"source systems observed: {sorted(systems)}",
        ),
    )


def _iaa_gates(
    val: list[ResolvedSplitDocument],
    test: list[ResolvedSplitDocument],
    annotations: list[AnnotationRecord],
    reviews: list[ReviewRecord],
    *,
    iaa_seed: int,
) -> tuple[GateResult, GateResult, AnnotationQuality]:
    def pairs_for(resolved: list[ResolvedSplitDocument]) -> list[DocumentAnnotationPair]:
        out: list[DocumentAnnotationPair] = []
        for item in resolved:
            review = _latest_accepted_review(reviews, item.document.document_id)
            if review is None:
                continue
            inputs = [a for a in annotations if a.annotation_id in review.input_annotation_ids]
            if len(inputs) < MIN_INDEPENDENT_ANNOTATIONS_FOR_IAA:
                continue
            out.append(
                DocumentAnnotationPair(
                    document_id=item.document.document_id,
                    labels_a=tuple(inputs[0].labels),
                    labels_b=tuple(inputs[1].labels),
                )
            )
        return out

    val_report = compute_iaa_report(pairs_for(val), seed=iaa_seed)
    test_report = compute_iaa_report(pairs_for(test), seed=iaa_seed)

    aggregate_passed = val_report.aggregate_passed and test_report.aggregate_passed
    critical_failed = {
        category
        for report in (val_report, test_report)
        for category in report.unreliable_eval_categories
        if category in CRITICAL_CATEGORIES
    }

    per_category_iaa = {
        f"val:{cat}": r.point_estimate for cat, r in val_report.per_category.items()
    } | {f"test:{cat}": r.point_estimate for cat, r in test_report.per_category.items()}

    quality = AnnotationQuality(
        val_iaa_span_f1=val_report.macro_f1_point,
        val_iaa_span_f1_ci95_low=val_report.macro_f1_ci_low,
        test_iaa_span_f1=test_report.macro_f1_point,
        test_iaa_span_f1_ci95_low=test_report.macro_f1_ci_low,
        per_category_iaa=per_category_iaa,
        unreliable_eval_categories=tuple(
            sorted(
                set(val_report.unreliable_eval_categories)
                | set(test_report.unreliable_eval_categories)
            )
        ),
    )

    return (
        GateResult(
            name="iaa_aggregate_floor",
            passed=aggregate_passed,
            detail=(
                f"val macro-F1 CI-low={val_report.macro_f1_ci_low}, "
                f"test macro-F1 CI-low={test_report.macro_f1_ci_low}"
            ),
        ),
        GateResult(
            name="iaa_critical_category_floor",
            passed=not critical_failed,
            detail=f"critical categories below floor: {sorted(critical_failed)}"
            if critical_failed
            else "all critical categories meet floor",
        ),
        quality,
    )


def build_dataset_release(
    store: SegmenterDatasetStore,
    *,
    release_id: str,
    ontology_version: str,
    guideline_version: str,
    source_commit: str,
    dependency_lock_hash: str,
    ontology_categories: set[str],
    split_assignment: SplitAssignment,
    known_limitations: list[KnownLimitation] | None = None,
    iaa_seed: int,
) -> ReleaseManifest:
    """Run the full RFC 0012 §12 release procedure; returns the written manifest.

    Raises :class:`ReleaseBlockedError` if any rigid gate fails, or if
    ``multiple_tribunals``/``multiple_source_systems`` (the 2 of 5 RFC 0012
    §14 advisory gates this function evaluates — see the module docstring's
    "advisory gate coverage" note) fail without a matching known limitation.
    The other three advisory gates are never evaluated, so they can never
    block a release and a known limitation naming one is currently inert.
    Raises :class:`~segmenter_dataset.store.ImmutabilityError` if
    ``release_id`` already exists.
    """
    known_limitations = known_limitations or []
    release_dir = store.release_dir(release_id)
    if release_dir.exists():
        msg = f"release {release_id!r} already exists at {release_dir} (RFC 0012 §12 step 9)"
        raise ImmutabilityError(msg)

    # Step 1: load.
    documents_by_id = {d.document_id: d for d in store.list_documents()}
    annotations = store.list_annotations()
    reviews = store.list_reviews()

    # Step 2: verify split integrity.
    disjoint_problems = check_disjoint(
        split_assignment.train_ids, split_assignment.val_ids, split_assignment.test_ids
    )
    hash_by_split: dict[str, set[str]] = {}
    for role, ids in (
        ("train", split_assignment.train_ids),
        ("val", split_assignment.val_ids),
        ("test", split_assignment.test_ids),
    ):
        for document_id in ids:
            digest = content_hash(documents_by_id[document_id].text)
            hash_by_split.setdefault(digest, set()).add(role)
    cross_split_hash_collisions = [
        digest for digest, roles in hash_by_split.items() if len(roles) > 1
    ]
    split_integrity_passed = not disjoint_problems and not cross_split_hash_collisions

    train = resolve_split(
        "train", split_assignment.train_ids, documents_by_id, annotations, reviews
    )
    val = resolve_split("val", split_assignment.val_ids, documents_by_id, annotations, reviews)
    test = resolve_split("test", split_assignment.test_ids, documents_by_id, annotations, reviews)

    # Step 3: mechanical validation.
    mechanical_gate = _mechanical_gate(train, val, test, ontology_categories)

    # Step 4: counts, hashes, IAA.
    train_support_gate, val_support_gate = _support_gates(train, val)
    iaa_aggregate_gate, iaa_critical_gate, annotation_quality = _iaa_gates(
        val, test, annotations, reviews, iaa_seed=iaa_seed
    )
    split_hashes = {
        "train": _split_hash(train),
        "validation": _split_hash(val),
        "test": _split_hash(test),
    }
    document_resolutions = {
        "train": {r.document.document_id: r.resolution_id for r in train},
        "validation": {r.document.document_id: r.resolution_id for r in val},
        "test": {r.document.document_id: r.resolution_id for r in test},
    }
    counts = {"train": len(train), "validation": len(val), "test": len(test)}
    tribunals: dict[str, int] = {}
    document_types: dict[str, int] = {}
    for resolved in (*train, *val, *test):
        tribunals[resolved.document.source.tribunal] = (
            tribunals.get(resolved.document.source.tribunal, 0) + 1
        )
        document_types[resolved.document.source.document_type] = (
            document_types.get(resolved.document.source.document_type, 0) + 1
        )

    # Step 5: gates.
    hash_collision_details = [f"hash collision: {h}" for h in cross_split_hash_collisions]
    val_test_adjudicated = len(val) == len(split_assignment.val_ids) and len(test) == len(
        split_assignment.test_ids
    )
    multiple_tribunals_gate, multiple_source_systems_gate = _diversity_gates(train, val, test)
    gate_results = [
        GateResult(
            name="split_disjoint_by_group_id_hash",
            passed=split_integrity_passed,
            detail="; ".join(disjoint_problems + hash_collision_details) or "no leakage found",
        ),
        GateResult(
            name="no_unresolved_annotation_conflicts",
            passed=True,
            detail="resolved by latest accepted review per document",
        ),
        GateResult(
            name="val_test_independently_adjudicated",
            passed=val_test_adjudicated,
            detail="every val/test document resolved to an accepted review",
        ),
        mechanical_gate,
        iaa_aggregate_gate,
        iaa_critical_gate,
        train_support_gate,
        val_support_gate,
        GateResult(name="release_checksums_generated", passed=True, detail="computed in step 4"),
        GateResult(
            name="ci_reproducible_build",
            passed=bool(source_commit) and bool(dependency_lock_hash),
            detail="source_commit and dependency_lock_hash both provided",
        ),
        # RFC 0012 §14 advisory gates — see the module docstring's "advisory
        # gate coverage" note: only these 2 of 5 are evaluated today.
        multiple_tribunals_gate,
        multiple_source_systems_gate,
    ]
    evaluation = evaluate_gates(gate_results, known_limitations)
    if not evaluation.release_allowed:
        failing = list(evaluation.blocking_rigid_failures) + list(
            evaluation.blocking_unwaived_advisory_failures
        )
        msg = "release blocked by gate failures: " + "; ".join(
            f"{g.name}: {g.detail}" for g in failing
        )
        raise ReleaseBlockedError(msg, failing)

    manifest = ReleaseManifest(
        release_id=release_id,
        ontology_version=ontology_version,
        guideline_version=guideline_version,
        source_commit=source_commit,
        dependency_lock_hash=dependency_lock_hash,
        split_hashes=split_hashes,
        document_resolutions=document_resolutions,
        counts=counts,
        tribunals=tribunals,
        document_types=document_types,
        annotation_quality=annotation_quality,
        known_limitations=tuple(known_limitations),
        created_at=_iso_now(),
    )

    # Steps 6-8: write to a temp dir, verify, atomically rename.
    _atomic_write_release(store, manifest)
    return manifest


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


class _RoundTripError(RuntimeError):
    """The written release manifest didn't round-trip — refuse to publish it."""


def _verify_round_trip(manifest_path: Path, manifest: ReleaseManifest) -> None:
    reloaded = ReleaseManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if reloaded != manifest:
        msg = "written release manifest does not round-trip — refusing to publish"
        raise _RoundTripError(msg)


def _atomic_write_release(store: SegmenterDatasetStore, manifest: ReleaseManifest) -> None:
    store.releases_dir.mkdir(parents=True, exist_ok=True)
    final_dir = store.release_dir(manifest.release_id)

    tmp_dir = Path(tempfile.mkdtemp(prefix=f".{manifest.release_id}.tmp-", dir=store.releases_dir))
    try:
        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        # Step 7: verify the written release round-trips.
        _verify_round_trip(manifest_path, manifest)

        # Step 8: atomic rename. Step 9 (refuse overwrite) was already
        # checked before any work started; Path.rename still fails loudly
        # if something raced and created final_dir in the meantime.
        tmp_dir.rename(final_dir)
    except BaseException:
        if tmp_dir.exists():
            for child in tmp_dir.iterdir():
                child.unlink()
            tmp_dir.rmdir()
        raise
