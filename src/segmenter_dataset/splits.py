"""Split policy (RFC 0012 §10): grouping, role eligibility, and leakage checks.

Split assignment happens only after a document reaches the state its target
role requires (RFC 0012 §10, fixed in review round 2 — there is no single
"after adjudication" rule for all three splits):

- **train** role requires only **annotated** (one complete annotation +
  mechanical validation; risk spot-review resolution is a maintainer
  process this module doesn't model — see RFC 0012 §9);
- **validation**/**test** roles require **adjudicated** (an accepted
  :class:`~segmenter_dataset.schemas.ReviewRecord`).

Grouping (so a related-document group never crosses splits) and the
disjointness/leakage primitives are adapted from PR #832's
``scripts/synthetic_segmenter/split_guard.py`` (RFC 0012 §18) — the
synthetic-lineage-specific helpers there (``assign_child_split``,
``require_train_only_sources``, ``calibration_eligible_ids``) are left
behind for PR 4/synthetic to reuse; they aren't RFC 0012's PR 1 concern.

``GroupingKeys.from_document`` is the real wiring, not a stub: it reads
persisted ``DocumentRecord.grouping`` metadata and falls back to regex
extraction (:mod:`segmenter_dataset.provenance`) for
``normalized_process_number`` when ingestion hasn't recorded one, so
union-find grouping fires on more than exact-content-hash and near-dup
ratio (PR #838 review finding #1). ``assign_splits`` additionally refuses
to return an empty val or test split when eval-eligible groups existed
(finding #2) — see :class:`EmptyEvalSplitError`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from segmenter_dataset.dedup import content_hash, find_near_duplicates
from segmenter_dataset.provenance import extract_normalized_process_number
from segmenter_dataset.schemas import SplitManifest


if TYPE_CHECKING:
    from segmenter_dataset.schemas import AnnotationRecord, DocumentRecord, ReviewRecord


class SplitLeakError(ValueError):
    """A split-integrity invariant (RFC 0012 §10) was violated."""


class EmptyEvalSplitError(ValueError):
    """RFC 0012 §10: eval-eligible groups existed, but ``assign_splits`` starved val or test.

    PR #838 review finding #2: the greedy packing in ``assign_splits`` only
    places a group into val/test if it fits entirely under the *remaining*
    target size — there is no fallback to "try a smaller group instead".
    Once grouping keys are real (finding #1: process number, family,
    parent/derived), eval-eligible groups routinely have >= 2 members, and a
    small target (e.g. 1, from a small overall eligible pool) can then
    silently starve val or test to zero — every group falls through to
    train with no error, because nothing overlaps (``SplitAssignment``'s
    disjointness check has nothing to catch). This is not a leakage
    condition, so it can't be folded into :class:`SplitLeakError`; it is
    checked directly in ``assign_splits``, right after packing.
    """


# ---------------------------------------------------------------------------
# Role eligibility
# ---------------------------------------------------------------------------


def train_eligible_document_ids(annotations: list[AnnotationRecord]) -> frozenset[str]:
    """Documents eligible for the **train** role: at least one annotation exists.

    Mechanical validation of each annotation is assumed to have already
    happened (``mechanical.validate_record``) before it reaches this
    function — this only checks presence, not correctness (RFC 0012 §3.2).
    """
    return frozenset(a.document_id for a in annotations)


def evaluation_eligible_document_ids(reviews: list[ReviewRecord]) -> frozenset[str]:
    """Documents eligible for the **validation**/**test** role: an accepted review exists."""
    return frozenset(r.document_id for r in reviews if r.status == "accepted")


# ---------------------------------------------------------------------------
# Grouping — a group never crosses splits (RFC 0012 §10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GroupingKeys:
    """Grouping keys for one document, per RFC 0012 §10 (all optional)."""

    document_id: str
    normalized_process_number: str | None = None
    source_process_id: str | None = None
    document_family: str | None = None
    parent_document_id: str | None = None

    @classmethod
    def from_document(cls, document: DocumentRecord) -> GroupingKeys:
        """Build real grouping keys for one document (RFC 0012 PR1 review finding #1).

        ``normalized_process_number`` prefers an explicitly recorded value
        (``document.grouping``, set by an ingestion pipeline with access to
        structured source metadata) and falls back to regex extraction from
        the document's own URI/text — see
        :func:`segmenter_dataset.provenance.extract_normalized_process_number`
        — when ingestion didn't record one. This is what makes
        process-number-based union-find grouping fire today, without
        waiting on a future ingestion PR to populate
        ``DocumentRecord.grouping``. The remaining keys aren't derivable
        from text alone and stay whatever ingestion recorded (``None``
        until it does).
        """
        grouping = document.grouping
        normalized_process_number = grouping.normalized_process_number
        if normalized_process_number is None:
            normalized_process_number = extract_normalized_process_number(
                source_uri=document.source.source_uri, text=document.text
            )
        return cls(
            document_id=document.document_id,
            normalized_process_number=normalized_process_number,
            source_process_id=grouping.source_process_id,
            document_family=grouping.document_family,
            parent_document_id=grouping.parent_document_id,
        )


class _UnionFind:
    """Minimal union-find for clustering documents that share any grouping key."""

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
    """Union every group of ids sharing a common key value."""
    for group_ids in id_lists.values():
        for other in group_ids[1:]:
            uf.union(group_ids[0], other)


def _union_by_content(
    uf: _UnionFind, documents: list[DocumentRecord], *, near_duplicate_threshold: float
) -> None:
    """Union documents sharing an exact content hash or a near-duplicate ratio."""
    by_hash: dict[str, list[str]] = {}
    for doc in documents:
        by_hash.setdefault(content_hash(doc.text), []).append(doc.document_id)
    _union_shared_values(uf, by_hash)

    texts = {doc.document_id: doc.text for doc in documents}
    for id_a, id_b, _ratio in find_near_duplicates(texts, threshold=near_duplicate_threshold):
        uf.union(id_a, id_b)


_GROUPING_KEY_FIELDS = ("normalized_process_number", "source_process_id", "document_family")


def _union_by_grouping_keys(uf: _UnionFind, keys: list[GroupingKeys]) -> None:
    """Union documents sharing a non-null grouping key or a parent/child relationship."""
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
    keys: list[GroupingKeys],
    *,
    near_duplicate_threshold: float = 0.9,
) -> dict[str, frozenset[str]]:
    """Cluster documents into groups that must not cross splits (RFC 0012 §10).

    Union-find over: exact content hash, near-duplicate content (via
    :func:`segmenter_dataset.dedup.find_near_duplicates`), and any shared
    non-null grouping key (process number, source process ID, document
    family, parent/derived relationship). Returns ``{group_id: {document_id, ...}}``
    keyed by one representative document_id per group.
    """
    ids = [doc.document_id for doc in documents]
    uf = _UnionFind(ids)

    _union_by_content(uf, documents, near_duplicate_threshold=near_duplicate_threshold)
    _union_by_grouping_keys(uf, keys)

    groups: dict[str, list[str]] = {}
    for doc_id in ids:
        root = uf.find(doc_id)
        groups.setdefault(root, []).append(doc_id)
    return {root: frozenset(members) for root, members in groups.items()}


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SplitAssignment:
    """Which split each document belongs to (RFC 0012 §10)."""

    train_ids: frozenset[str]
    val_ids: frozenset[str]
    test_ids: frozenset[str]

    def __post_init__(self) -> None:
        """Raise :class:`SplitLeakError` immediately if the three sets aren't disjoint."""
        violations = check_disjoint(self.train_ids, self.val_ids, self.test_ids)
        if violations:
            raise SplitLeakError("; ".join(violations))

    def split_of(self, document_id: str) -> str | None:
        """Return ``"train"``/``"val"``/``"test"`` for a known document_id, else ``None``."""
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
    """Return violation messages for any pairwise intersection; empty = OK."""
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
    """Deterministically assign groups to train/val/test (RFC 0012 §10).

    A group is **evaluation-capable** (may become val or test) only if
    every one of its documents is ``evaluation_eligible``; otherwise it can
    only become train, and only once every member is at least
    ``train_eligible``. Documents that are in neither eligible set are
    dropped from the group before assignment (not yet ready for any role —
    not an error).

    Deterministic: groups are ordered by a stable hash of ``(seed,
    group_id)`` before greedy proportional assignment, so the same inputs
    always produce the same split — reproducibility (RFC 0012 §12/§14), not
    an actual pseudo-random shuffle.
    """

    def sort_key(group_id: str) -> str:
        return hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()

    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()

    ordered_group_ids = sorted(groups, key=sort_key)
    total_eligible = sum(
        len(groups[gid] & (train_eligible | evaluation_eligible)) for gid in ordered_group_ids
    )
    if total_eligible == 0:
        return SplitAssignment(frozenset(), frozenset(), frozenset())

    val_target = max(1, round(total_eligible * val_ratio))
    test_target = max(1, round(total_eligible * (1 - train_ratio - val_ratio)))

    any_evaluation_capable_group = False
    for group_id in ordered_group_ids:
        members = groups[group_id] & (train_eligible | evaluation_eligible)
        if not members:
            continue
        evaluation_capable = members <= evaluation_eligible
        any_evaluation_capable_group = any_evaluation_capable_group or evaluation_capable

        if (
            evaluation_capable
            and len(val_ids) < val_target
            and len(val_ids) + len(members) <= val_target
        ):
            val_ids |= members
        elif (
            evaluation_capable
            and len(test_ids) < test_target
            and len(test_ids) + len(members) <= test_target
        ):
            test_ids |= members
        else:
            train_ids |= members

    if any_evaluation_capable_group and (not val_ids or not test_ids):
        msg = (
            "eval-eligible groups exist but assign_splits produced an empty "
            f"val ({len(val_ids)} docs) or test ({len(test_ids)} docs) split — "
            "every eligible group likely exceeds the remaining target size, "
            "with no fallback to a smaller group (RFC 0012 §10, PR #838 review "
            "finding #2); widen val_ratio/test_ratio or grow the pool of "
            "independent eval-eligible documents before re-running"
        )
        raise EmptyEvalSplitError(msg)

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


# ---------------------------------------------------------------------------
# Leakage rejection (RFC 0012 §10's explicit reject list)
# ---------------------------------------------------------------------------


def validate_split_leakage(
    assignment: SplitAssignment,
    documents: list[DocumentRecord],
    groups: dict[str, frozenset[str]],
) -> list[str]:
    """RFC 0012 §10's explicit rejection checks; empty list = no leakage found.

    Checks: no ``document_id`` assigned twice (covered structurally by
    ``SplitAssignment``'s disjointness, re-asserted here for a single
    combined report), no normalized-content-hash collision across splits,
    and no group spanning more than one split.
    """
    problems: list[str] = []

    hash_to_splits: dict[str, set[str]] = {}
    for doc in documents:
        split = assignment.split_of(doc.document_id)
        if split is None:
            continue
        hash_to_splits.setdefault(content_hash(doc.text), set()).add(split)
    problems.extend(
        f"content_hash {digest} appears in multiple splits: {sorted(splits)}"
        for digest, splits in hash_to_splits.items()
        if len(splits) > 1
    )

    for group_id, members in groups.items():
        splits_seen = {
            assignment.split_of(doc_id)
            for doc_id in members
            if assignment.split_of(doc_id) is not None
        }
        if len(splits_seen) > 1:
            problems.append(
                f"group {group_id} spans multiple splits: {sorted(splits_seen)} "
                f"(members: {sorted(members)})"
            )

    return problems


def validate_cross_pool_leakage(
    candidate_documents: list[DocumentRecord],
    *,
    existing_document_ids: frozenset[str] = frozenset(),
    existing_content_hashes: frozenset[str] = frozenset(),
    existing_texts: dict[str, str] | None = None,
    near_duplicate_threshold: float = 0.9,
) -> list[str]:
    """Reject candidates reusing a document_id/content_hash from another pool.

    ``validate_split_leakage`` above only sees documents loaded into one
    ``assign_splits`` call. Freezing a new locked holdout (RFC 0012 §10's
    reject list, per #884) instead needs to check a separately-assembled
    candidate pool against splits persisted earlier — train/validation, or a
    retired test split — without re-loading their full ``DocumentRecord``s;
    only their previously-recorded ``document_id``s, content hashes and (for
    the near-duplicate check, RFC 0012 §10/§16.1) text.

    ``existing_texts`` is optional because callers auditing only
    document_id/content_hash reuse (e.g. against a pool whose full text was
    never persisted) still get that coverage without it.
    """
    problems: list[str] = []
    for doc in candidate_documents:
        if doc.document_id in existing_document_ids:
            problems.append(f"document_id {doc.document_id} already used in an existing split")
        digest = content_hash(doc.text)
        if digest in existing_content_hashes:
            problems.append(
                f"content_hash {digest} (document_id {doc.document_id}) already used "
                "in an existing split"
            )

    if existing_texts:
        candidate_texts = {doc.document_id: doc.text for doc in candidate_documents}
        candidate_ids = frozenset(candidate_texts)
        merged_texts = {**existing_texts, **candidate_texts}
        for id_a, id_b, ratio in find_near_duplicates(
            merged_texts, threshold=near_duplicate_threshold
        ):
            # Only a candidate-vs-existing pair is cross-pool leakage; a pair
            # entirely within one side is that side's own concern.
            if (id_a in candidate_ids) == (id_b in candidate_ids):
                continue
            candidate_id, existing_id = (id_a, id_b) if id_a in candidate_ids else (id_b, id_a)
            problems.append(
                f"near-duplicate: candidate {candidate_id} matches existing {existing_id} "
                f"at ratio {ratio:.3f} (>= {near_duplicate_threshold})"
            )

    return problems
