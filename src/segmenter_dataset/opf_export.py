"""Bridge a built release (RFC 0012 §8/§12) to OPF's training JSONL format (RFC 0012 §15 PR3).

OPF (``openai/privacy-filter``) trains from JSONL where each line is
``{"text": ..., "label": [{"category", "start", "end"}], "info": {...}}`` plus a
sibling ``label_space.json`` (``span_class_names`` with ``"O"`` first). This module
produces exactly that from a :class:`~segmenter_dataset.schemas.ReleaseManifest` —
never from "whatever the store's latest annotations happen to be", because a release
is immutable (RFC 0012 §3.1/§12) and re-deriving training data for it after the fact
must reproduce the *exact* records the release pinned, not drift with later edits to
the store. ``document_resolutions`` is exactly what makes that possible: it names the
specific ``annotation_id`` (train) or ``review_id`` (validation/test) each document
resolved to, so :func:`resolve_release_documents` looks those up by ID rather than
asking the store for "the latest one".

Train exports every category the ontology defines, using ``AnnotationRecord.labels``
as-is; validation/test export ``ReviewRecord.final_labels`` — the adjudicated result,
never a raw pre-adjudication annotation (RFC 0012 §9's independence requirement would
be meaningless if training data leaked back in through the eval split).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path

    from segmenter_dataset.schemas import (
        AnnotationRecord,
        DocumentRecord,
        Label,
        ReleaseManifest,
        ReviewRecord,
    )
    from segmenter_dataset.store import SegmenterDatasetStore


# RFC 0012 §10/§12: role names as they appear in ReleaseManifest.document_resolutions
# vs. the file names OPF-facing tooling in this repo already uses
# (scripts/train_decision_segmenter.py) — kept distinct so a manifest role rename
# doesn't silently rename files a training script hardcodes.
_ROLE_TO_FILENAME = {"train": "train", "validation": "val", "test": "test"}


class ReleaseResolutionError(LookupError):
    """A release's ``document_resolutions`` names an annotation/review the store no longer has.

    Should be impossible for an immutable store (RFC 0012 §3.1) — records are never
    deleted — so this indicates store corruption or a release manifest from a
    different store, not an expected runtime condition.
    """


def _find_annotation(
    store: SegmenterDatasetStore, document_id: str, annotation_id: str
) -> AnnotationRecord:
    for annotation in store.list_annotations(document_id=document_id):
        if annotation.annotation_id == annotation_id:
            return annotation
    message = f"annotation {annotation_id!r} for document {document_id!r} not found in store"
    raise ReleaseResolutionError(message)


def _find_review(store: SegmenterDatasetStore, document_id: str, review_id: str) -> ReviewRecord:
    for review in store.list_reviews(document_id=document_id):
        if review.review_id == review_id:
            return review
    message = f"review {review_id!r} for document {document_id!r} not found in store"
    raise ReleaseResolutionError(message)


def resolve_release_documents(
    store: SegmenterDatasetStore, manifest: ReleaseManifest
) -> dict[str, list[tuple[DocumentRecord, list[Label]]]]:
    """Re-read the exact ``(document, labels)`` pairs a built release pinned.

    Keyed by role ("train"/"validation"/"test"), each list holding the resolved
    document plus the labels from the *specific* annotation/review
    ``document_resolutions`` names — not the store's current latest.
    """
    resolved: dict[str, list[tuple[DocumentRecord, list[Label]]]] = {}
    for role, resolutions in manifest.document_resolutions.items():
        items: list[tuple[DocumentRecord, list[Label]]] = []
        for document_id, resolution_id in sorted(resolutions.items()):
            document = store.read_document(document_id)
            if role == "train":
                labels = _find_annotation(store, document_id, resolution_id).labels
            else:
                labels = _find_review(store, document_id, resolution_id).final_labels
            items.append((document, list(labels)))
        resolved[role] = items
    return resolved


def to_opf_record(document: DocumentRecord, labels: list[Label]) -> dict:
    """One OPF JSONL record for ``document`` — spans sorted by position for readability."""
    ordered = sorted(labels, key=lambda label: (label.start, label.end))
    return {
        "text": document.text,
        "label": [
            {"category": label.category, "start": label.start, "end": label.end}
            for label in ordered
        ],
        "info": {
            "document_id": document.document_id,
            "source_uri": document.source.source_uri,
            "tribunal": document.source.tribunal,
            "document_type": document.source.document_type,
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    """Write ``records`` to ``path`` as one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False))
            handle.write("\n")


def write_label_space(path: Path, ontology_categories: set[str], ontology_version: str) -> None:
    """``O`` first, then every trainable category sorted — the opf-finetune skill's contract."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "span_class_names": ["O", *sorted(ontology_categories)],
        "category_version": ontology_version,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_release_for_training(
    store: SegmenterDatasetStore,
    manifest: ReleaseManifest,
    output_dir: Path,
    ontology_categories: set[str],
) -> dict[str, int]:
    """Write ``train.jsonl``/``val.jsonl``/``test.jsonl`` + ``label_space.json`` to ``output_dir``.

    Returns record counts per file, for the caller to log/verify against the
    release manifest's own ``counts`` field. Writing ``test.jsonl`` here does not
    grant permission to read it — RFC 0012 §3.3/§13.1 gate that separately; this
    function's job is reproducing the release's data, not enforcing who may look
    at which file.
    """
    resolved = resolve_release_documents(store, manifest)
    counts: dict[str, int] = {}
    for role, filename in _ROLE_TO_FILENAME.items():
        items = resolved.get(role, [])
        records = [to_opf_record(document, labels) for document, labels in items]
        write_jsonl(output_dir / f"{filename}.jsonl", records)
        counts[filename] = len(records)
    write_label_space(
        output_dir / "label_space.json", ontology_categories, manifest.ontology_version
    )
    return counts
