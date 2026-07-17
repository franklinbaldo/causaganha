"""Immutable dataset release builder (RFC 0012 §12)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from segmenter_dataset import mechanical
from segmenter_dataset.gates import GateResult, evaluate_gates
from segmenter_dataset.iaa import (
    DEFAULT_BOOTSTRAP_RESAMPLES,
    DocumentAnnotationPair,
    compute_iaa_report,
)
from segmenter_dataset.schemas import (
    AnnotationQuality,
    AnnotationRecord,
    DocumentRecord,
    KnownLimitation,
    Label,
    ReleaseManifest,
    ReviewRecord,
    SplitManifest,
)
from segmenter_dataset.splits import (
    assignment_from_manifest,
    build_groups,
    validate_split_leakage,
)
from segmenter_dataset.store import ImmutabilityError, SegmenterDatasetStore


CRITICAL_CATEGORIES = frozenset(
    {
        "dispositivo_abertura",
        "resultado",
        "acordao_decisorio_inicio",
        "acordao_decisorio_fim",
    }
)
MIN_TRAIN_SUPPORT_PER_CATEGORY = 10
MIN_VAL_SUPPORT_PER_CATEGORY = 5
_SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleaseBlockedError(RuntimeError):
    """A rigid or unwaived advisory gate blocked the release."""

    def __init__(self, message: str, gate_results: list[GateResult]) -> None:
        super().__init__(message)
        self.gate_results = gate_results


@dataclass(frozen=True)
class ResolvedSplitDocument:
    document: DocumentRecord
    labels: list[Label]
    allowed_unmatched: dict[str, str]
    resolution_id: str
    input_annotation_ids: tuple[str, ...] = ()


def _latest(items: list, document_id: str, *, timestamp: str, accepted: bool = False):
    matches = [item for item in items if item.document_id == document_id]
    if accepted:
        matches = [item for item in matches if item.status == "accepted"]
    return max(matches, key=lambda item: getattr(item, timestamp)) if matches else None


def _resolve_split(
    role: str,
    document_ids: frozenset[str],
    documents: dict[str, DocumentRecord],
    annotations: list[AnnotationRecord],
    reviews: list[ReviewRecord],
    *,
    ontology_version: str,
    ontology_categories: set[str],
) -> tuple[list[ResolvedSplitDocument], list[str]]:
    resolved: list[ResolvedSplitDocument] = []
    problems: list[str] = []
    annotations_by_id = {item.annotation_id: item for item in annotations}

    for document_id in sorted(document_ids):
        document = documents.get(document_id)
        if document is None:
            problems.append(f"{role} references missing document {document_id}")
            continue
        if role == "train":
            annotation = _latest(annotations, document_id, timestamp="completed_at")
            if annotation is None:
                problems.append(f"train document {document_id} has no annotation")
                continue
            if annotation.ontology_version != ontology_version:
                problems.append(
                    f"train annotation {annotation.annotation_id} uses "
                    f"{annotation.ontology_version}, expected {ontology_version}"
                )
            unknown = set(annotation.covered_categories) - ontology_categories
            if unknown:
                problems.append(
                    f"train annotation {annotation.annotation_id} covers unknown "
                    f"categories {sorted(unknown)}"
                )
            resolved.append(
                ResolvedSplitDocument(
                    document,
                    annotation.labels,
                    annotation.allowed_unmatched,
                    annotation.annotation_id,
                )
            )
            continue

        review = _latest(
            reviews,
            document_id,
            timestamp="approved_at",
            accepted=True,
        )
        if review is None:
            problems.append(f"{role} document {document_id} has no accepted review")
            continue
        problems.extend(
            f"[{role}:{document_id}] {problem}"
            for problem in mechanical.validate_review_lineage(
                review,
                annotations_by_id,
                ontology_version=ontology_version,
                ontology_categories=ontology_categories,
            )
        )
        resolved.append(
            ResolvedSplitDocument(
                document,
                review.final_labels,
                review.allowed_unmatched,
                review.review_id,
                review.input_annotation_ids,
            )
        )
    return resolved, problems


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _split_hash(items: list[ResolvedSplitDocument]) -> str:
    payload = [
        [item.document.document_id, item.resolution_id]
        for item in sorted(items, key=lambda item: item.document.document_id)
    ]
    return _sha256(json.dumps(payload, separators=(",", ":")))


def _category_counts(items: list[ResolvedSplitDocument]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        for label in item.labels:
            counts[label.category] = counts.get(label.category, 0) + 1
    return counts


def _support_gates(
    train: list[ResolvedSplitDocument],
    val: list[ResolvedSplitDocument],
    ontology: set[str],
) -> tuple[GateResult, GateResult]:
    def below(items: list[ResolvedSplitDocument], floor: int) -> dict[str, int]:
        counts = _category_counts(items)
        return {
            category: counts.get(category, 0)
            for category in sorted(ontology)
            if counts.get(category, 0) < floor
        }

    train_below = below(train, MIN_TRAIN_SUPPORT_PER_CATEGORY)
    val_below = below(val, MIN_VAL_SUPPORT_PER_CATEGORY)
    return (
        GateResult(
            "train_minimum_support_per_category",
            not train_below,
            f"below floor: {train_below}" if train_below else "all categories meet floor",
        ),
        GateResult(
            "val_minimum_support_for_reported_metrics",
            not val_below,
            f"below floor: {val_below}" if val_below else "all categories meet floor",
        ),
    )


def _mechanical_gate(
    splits: dict[str, list[ResolvedSplitDocument]], ontology: set[str]
) -> GateResult:
    problems = [
        f"[{role}:{item.document.document_id}] {problem}"
        for role, items in splits.items()
        for item in items
        for problem in mechanical.validate_record(
            item.document.text,
            item.labels,
            ontology,
            allowed_unmatched=item.allowed_unmatched,
        )
    ]
    return GateResult(
        "ontology_schema_valid",
        not problems,
        "; ".join(problems[:20]) if problems else "all records mechanically valid",
    )


def _iaa_gates(
    val: list[ResolvedSplitDocument],
    test: list[ResolvedSplitDocument],
    annotations: list[AnnotationRecord],
    *,
    seed: int,
    resamples: int,
) -> tuple[GateResult, GateResult, AnnotationQuality]:
    by_id = {item.annotation_id: item for item in annotations}

    def pairs(items: list[ResolvedSplitDocument]) -> list[DocumentAnnotationPair]:
        result = []
        for item in items:
            if len(item.input_annotation_ids) != 2:
                continue
            first, second = (by_id.get(value) for value in item.input_annotation_ids)
            if first is not None and second is not None:
                result.append(
                    DocumentAnnotationPair(
                        item.document.document_id,
                        tuple(first.labels),
                        tuple(second.labels),
                    )
                )
        return result

    val_report = compute_iaa_report(pairs(val), seed=seed, resamples=resamples)
    test_report = compute_iaa_report(pairs(test), seed=seed, resamples=resamples)
    unreliable = set(val_report.unreliable_eval_categories) | set(
        test_report.unreliable_eval_categories
    )
    critical = unreliable & CRITICAL_CATEGORIES
    per_category = {
        f"val:{key}": value.point_estimate for key, value in val_report.per_category.items()
    } | {f"test:{key}": value.point_estimate for key, value in test_report.per_category.items()}
    quality = AnnotationQuality(
        val_iaa_span_f1=val_report.macro_f1_point,
        val_iaa_span_f1_ci95_low=val_report.macro_f1_ci_low,
        test_iaa_span_f1=test_report.macro_f1_point,
        test_iaa_span_f1_ci95_low=test_report.macro_f1_ci_low,
        per_category_iaa=per_category,
        unreliable_eval_categories=tuple(sorted(unreliable)),
    )
    return (
        GateResult(
            "iaa_aggregate_floor",
            val_report.aggregate_passed and test_report.aggregate_passed,
            f"val CI-low={val_report.macro_f1_ci_low}; test CI-low={test_report.macro_f1_ci_low}",
        ),
        GateResult(
            "iaa_critical_category_floor",
            not critical,
            f"critical categories below floor: {sorted(critical)}"
            if critical
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
    ci_provider: str,
    ci_run_id: str,
    ontology_categories: set[str],
    split_manifest: SplitManifest,
    known_limitations: list[KnownLimitation] | None = None,
    iaa_seed: int,
    iaa_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> ReleaseManifest:
    """Build, verify and atomically publish one dataset release."""
    known_limitations = known_limitations or []
    if store.release_dir(release_id).exists():
        raise ImmutabilityError(f"release {release_id!r} already exists")

    all_documents = store.list_documents()
    documents = {item.document_id: item for item in all_documents}
    annotations = store.list_annotations()
    reviews = store.list_reviews()
    assignment = assignment_from_manifest(split_manifest)
    groups = build_groups(
        all_documents,
        near_duplicate_threshold=split_manifest.near_duplicate_threshold,
    )
    recorded_groups = {frozenset(value) for value in split_manifest.groups.values()}
    recomputed_groups = {frozenset(value) for value in groups.values()}
    leakage = validate_split_leakage(assignment, all_documents, groups)
    if recorded_groups != recomputed_groups:
        leakage.append("split manifest groups differ from recomputed groups")

    resolved: dict[str, list[ResolvedSplitDocument]] = {}
    problems: dict[str, list[str]] = {}
    for role, ids in (
        ("train", assignment.train_ids),
        ("validation", assignment.val_ids),
        ("test", assignment.test_ids),
    ):
        resolved[role], problems[role] = _resolve_split(
            "val" if role == "validation" else role,
            ids,
            documents,
            annotations,
            reviews,
            ontology_version=ontology_version,
            ontology_categories=ontology_categories,
        )

    support = _support_gates(resolved["train"], resolved["validation"], ontology_categories)
    iaa_aggregate, iaa_critical, quality = _iaa_gates(
        resolved["validation"],
        resolved["test"],
        annotations,
        seed=iaa_seed,
        resamples=iaa_resamples,
    )
    split_hashes = {role: _split_hash(items) for role, items in resolved.items()}
    split_manifest_hash = _sha256(split_manifest.model_dump_json())
    resolution_problems = sum(problems.values(), [])
    eval_problems = problems["validation"] + problems["test"]
    checksum_ok = bool(_SHA256_RE.fullmatch(split_manifest_hash)) and all(
        _SHA256_RE.fullmatch(value) for value in split_hashes.values()
    )
    provenance_ok = (
        bool(_SHA40_RE.fullmatch(source_commit))
        and bool(_SHA256_RE.fullmatch(dependency_lock_hash))
        and bool(ci_provider.strip())
        and bool(ci_run_id.strip())
    )

    gates = [
        GateResult(
            "split_disjoint_by_group_id_hash",
            not leakage,
            "; ".join(leakage) if leakage else "no leakage found",
        ),
        GateResult(
            "no_unresolved_annotation_conflicts",
            not resolution_problems,
            "; ".join(resolution_problems[:20]) if resolution_problems else "all lineage resolves",
        ),
        GateResult(
            "val_test_independently_adjudicated",
            not eval_problems
            and len(resolved["validation"]) == len(assignment.val_ids)
            and len(resolved["test"]) == len(assignment.test_ids),
            "; ".join(eval_problems[:20])
            if eval_problems
            else "all evaluation documents independently adjudicated",
        ),
        _mechanical_gate(resolved, ontology_categories),
        iaa_aggregate,
        iaa_critical,
        *support,
        GateResult(
            "release_checksums_generated",
            checksum_ok,
            "release hashes computed" if checksum_ok else "invalid release hashes",
        ),
        GateResult(
            "ci_reproducible_build",
            provenance_ok,
            "complete CI provenance" if provenance_ok else "invalid build provenance",
        ),
    ]
    evaluation = evaluate_gates(gates, known_limitations)
    if not evaluation.release_allowed:
        failures = [
            *evaluation.blocking_rigid_failures,
            *evaluation.blocking_unwaived_advisory_failures,
        ]
        raise ReleaseBlockedError(
            "release blocked: " + "; ".join(f"{item.name}: {item.detail}" for item in failures),
            failures,
        )

    manifest = ReleaseManifest(
        release_id=release_id,
        ontology_version=ontology_version,
        guideline_version=guideline_version,
        source_commit=source_commit,
        dependency_lock_hash=dependency_lock_hash,
        ci_provider=ci_provider,
        ci_run_id=ci_run_id,
        split_manifest_hash=split_manifest_hash,
        split_hashes=split_hashes,
        document_resolutions={
            role: {item.document.document_id: item.resolution_id for item in items}
            for role, items in resolved.items()
        },
        counts={role: len(items) for role, items in resolved.items()},
        tribunals=_source_counts(resolved, "tribunal"),
        document_types=_source_counts(resolved, "document_type"),
        annotation_quality=quality,
        iaa_seed=iaa_seed,
        iaa_resamples=iaa_resamples,
        known_limitations=tuple(known_limitations),
        created_at=datetime.now(UTC).isoformat(),
    )
    _atomic_write_release(store, manifest, split_manifest)
    return manifest


def _source_counts(splits: dict[str, list[ResolvedSplitDocument]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for items in splits.values():
        for item in items:
            value = getattr(item.document.source, field)
            counts[value] = counts.get(value, 0) + 1
    return counts


def _atomic_write_release(
    store: SegmenterDatasetStore,
    manifest: ReleaseManifest,
    split_manifest: SplitManifest,
) -> None:
    store.releases_dir.mkdir(parents=True, exist_ok=True)
    final_dir = store.release_dir(manifest.release_id)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{manifest.release_id}.tmp-", dir=store.releases_dir)
    )
    try:
        artifacts = {
            "manifest.json": manifest.model_dump_json(indent=2),
            "split_manifest.json": split_manifest.model_dump_json(indent=2),
        }
        for name, content in artifacts.items():
            (temporary / name).write_text(content, encoding="utf-8")
        checksums = {name: _sha256(content) for name, content in artifacts.items()}
        (temporary / "checksums.sha256").write_text(
            "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
            encoding="utf-8",
        )
        if ReleaseManifest.model_validate_json(artifacts["manifest.json"]) != manifest:
            raise RuntimeError("manifest does not round-trip")
        if SplitManifest.model_validate_json(artifacts["split_manifest.json"]) != split_manifest:
            raise RuntimeError("split manifest does not round-trip")
        for name, expected in checksums.items():
            if _sha256((temporary / name).read_text(encoding="utf-8")) != expected:
                raise RuntimeError(f"checksum verification failed for {name}")
        temporary.rename(final_dir)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
