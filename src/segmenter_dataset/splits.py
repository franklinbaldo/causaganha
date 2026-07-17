"""Split policy: grouping, role eligibility, deterministic assignment, leakage checks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from segmenter_dataset.dedup import content_hash, find_near_duplicates
from segmenter_dataset.schemas import SplitManifest


if TYPE_CHECKING:
    from segmenter_dataset.schemas import AnnotationRecord, DocumentRecord, ReviewRecord


class SplitLeakError(ValueError):
    """A split-integrity invariant was violated."""


def train_eligible_document_ids(annotations: list[AnnotationRecord]) -> frozenset[str]:
    """Return documents with at least one annotation for train eligibility."""
    return frozenset(annotation.document_id for annotation in annotations)


def evaluation_eligible_document_ids(reviews: list[ReviewRecord]) -> frozenset[str]:
    """Return documents with an accepted review for evaluation eligibility."""
    return frozenset(review.document_id for review in reviews if review.status == "accepted")


@dataclass(frozen=True)
class GroupingKeys:
    """Grouping keys for one document."""

    document_id: str
    normalized_process_number: str | None = None
    source_process_id: str | None = None
    document_family: str | None = None
    parent_document_id: str | None = None

    @classmethod
    def from_document(cls, document: DocumentRecord) -> GroupingKeys:
        """Build grouping keys from persisted document metadata."""
        grouping = document.grouping
        return cls(
            document_id=document.document_id,
            normalized_process_number=grouping.normalized_process_number,
            source_process_id=grouping.source_process_id,
            document_family=grouping.document_family,
            parent_document_id=grouping.parent_document_id,
        )


class _UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self._parent = {doc_id: doc_id for doc_id in ids}

    def find(self, doc_id: str) -> str:
        while self._parent[doc_id] != doc_id:
            self._parent[doc_id] = self._parent[self._parent[doc_id]]
            doc_id = self._parent[doc_id]
        return doc_id

    def union(self, a: str, b: str) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self._parent[root_a] = root_b

    def contains(self, doc_id: str) -> bool:
        return doc_id in self._parent


def _union_shared_values(uf: _UnionFind, id_lists: dict[str, list[str]]) -> None:
    for ids in id_lists.values():
        for other in ids[1:]:
            uf.union(ids[0], other)


def _union_by_content(
    uf: _UnionFind,
    documents: list[DocumentRecord],
    *,
    near_duplicate_threshold: float,
) -> None:
    by_hash: dict[str, list[str]] = {}
    for document in documents:
        by_hash.setdefault(content_hash(document.text), []).append(document.document_id)
    _union_shared_values(uf, by_hash)

    texts = {document.document_id: document.text for document in documents}
    for id_a, id_b, _ratio in find_near_duplicates(texts, threshold=near_duplicate_threshold):
        uf.union(id_a, id_b)


_GROUPING_KEY_FIELDS = (
    "normalized_process_number",
    "source_process_id",
    "document_family",
)


def _union_by_grouping_keys(uf: _UnionFind, keys: list[GroupingKeys]) -> None:
    for field in _GROUPING_KEY_FIELDS:
        by_key: dict[str, list[str]] = {}
        for key in keys:
            value = getattr(key, field)
            if value:
                by_key.setdefault(value, []).append(key.document_id)
        _union_shared_values(uf, by_key)

    for key in keys:
        if key.parent_document_id and uf.contains(key.parent_document_id):
            uf.union(key.document_id, key.parent_document_id)


def build_groups(
    documents: list[DocumentRecord],
    keys: list[GroupingKeys] | None = None,
    *,
    near_duplicate_threshold: float = 0.9,
) -> dict[str, frozenset[str]]:
    """Cluster documents using content, process, family and parent relationships."""
    keys = keys or [GroupingKeys.from_document(document) for document in documents]
    document_ids = {document.document_id for document in documents}
    key_ids = {key.document_id for key in keys}
    if key_ids != document_ids:
        missing = sorted(document_ids - key_ids)
        extra = sorted(key_ids - document_ids)
        message = f"grouping keys do not match documents: missing={missing}, extra={extra}"
        raise SplitLeakError(message)

    uf = _UnionFind(sorted(document_ids))
    _union_by_content(uf, documents, near_duplicate_threshold=near_duplicate_threshold)
    _union_by_grouping_keys(uf, keys)

    groups: dict[str, list[str]] = {}
    for document_id in sorted(document_ids):
        groups.setdefault(uf.find(document_id), []).append(document_id)
    return {root: frozenset(members) for root, members in groups.items()}


@dataclass(frozen=True)
class SplitAssignment:
    """Disjoint document IDs assigned to train, validation, and test."""

    train_ids: frozenset[str]
    val_ids: frozenset[str]
    test_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Reject overlapping split assignments immediately."""
        violations = check_disjoint(self.train_ids, self.val_ids, self.test_ids)
        if violations:
            message = "; ".join(violations)
            raise SplitLeakError(message)

    def split_of(self, document_id: str) -> str | None:
        """Return the assigned split for a document, if any."""
        if document_id in self.train_ids:
            return "train"
        if document_id in self.val_ids:
            return "val"
        if document_id in self.test_ids:
            return "test"
        return None


def check_disjoint(
    train_ids: frozenset[str], val_ids: frozenset[str], test_ids: frozenset[str]
) -> list[str]:
    """Return pairwise overlap violations between split ID sets."""
    violations: list[str] = []
    for name_a, ids_a, name_b, ids_b in (
        ("train", train_ids, "val", val_ids),
        ("train", train_ids, "test", test_ids),
        ("val", val_ids, "test", test_ids),
    ):
        overlap = ids_a & ids_b
        if overlap:
            violations.append(f"{name_a}/{name_b} overlap: {sorted(overlap)}")
    return violations


def assign_splits(
    groups: dict[str, frozenset[str]],
    *,
    train_eligible: frozenset[str],
    evaluation_eligible: frozenset[str],
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int,
) -> SplitAssignment:
    """Deterministically assign whole groups without splitting related documents."""
    if not (0 < train_ratio < 1 and 0 < val_ratio < 1 and train_ratio + val_ratio < 1):
        message = "invalid train/validation ratios"
        raise ValueError(message)

    def sort_key(group_id: str) -> str:
        return hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()

    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()
    ordered = sorted(groups, key=sort_key)
    total = sum(
        len(groups[group_id] & (train_eligible | evaluation_eligible)) for group_id in ordered
    )
    if total == 0:
        return SplitAssignment(frozenset(), frozenset(), frozenset())

    val_target = max(1, round(total * val_ratio))
    test_target = max(1, round(total * (1 - train_ratio - val_ratio)))

    for group_id in ordered:
        members = groups[group_id] & (train_eligible | evaluation_eligible)
        if not members:
            continue
        if members <= evaluation_eligible:
            val_deficit = val_target - len(val_ids)
            test_deficit = test_target - len(test_ids)
            if val_deficit > 0 or test_deficit > 0:
                if val_deficit >= test_deficit:
                    val_ids |= members
                else:
                    test_ids |= members
                continue
        train_ids |= members

    return SplitAssignment(frozenset(train_ids), frozenset(val_ids), frozenset(test_ids))


def create_split_manifest(
    assignment: SplitAssignment,
    groups: dict[str, frozenset[str]],
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    near_duplicate_threshold: float,
) -> SplitManifest:
    """Create a reproducible split manifest with assignment parameters."""
    return SplitManifest(
        train_ids=tuple(sorted(assignment.train_ids)),
        val_ids=tuple(sorted(assignment.val_ids)),
        test_ids=tuple(sorted(assignment.test_ids)),
        seed=seed,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        near_duplicate_threshold=near_duplicate_threshold,
        groups={group_id: tuple(sorted(members)) for group_id, members in sorted(groups.items())},
    )


def assignment_from_manifest(manifest: SplitManifest) -> SplitAssignment:
    """Reconstruct the split assignment encoded in a manifest."""
    return SplitAssignment(
        train_ids=frozenset(manifest.train_ids),
        val_ids=frozenset(manifest.val_ids),
        test_ids=frozenset(manifest.test_ids),
    )


def validate_split_leakage(
    assignment: SplitAssignment,
    documents: list[DocumentRecord],
    groups: dict[str, frozenset[str]],
) -> list[str]:
    """Return ID, exact-hash, or grouping leakage violations."""
    problems = check_disjoint(assignment.train_ids, assignment.val_ids, assignment.test_ids)

    hash_to_splits: dict[str, set[str]] = {}
    for document in documents:
        split = assignment.split_of(document.document_id)
        if split is not None:
            hash_to_splits.setdefault(content_hash(document.text), set()).add(split)
    problems.extend(
        f"content_hash {digest} appears in multiple splits: {sorted(splits)}"
        for digest, splits in hash_to_splits.items()
        if len(splits) > 1
    )

    for group_id, members in groups.items():
        splits_seen = {
            assignment.split_of(document_id)
            for document_id in members
            if assignment.split_of(document_id) is not None
        }
        if len(splits_seen) > 1:
            problems.append(
                f"group {group_id} spans multiple splits: {sorted(splits_seen)} "
                f"(members: {sorted(members)})"
            )
    return problems
