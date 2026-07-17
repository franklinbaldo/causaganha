"""Filesystem layout for the segmenter dataset lifecycle (RFC 0012 §8).

```text
data/segmenter/
  documents/<document_id>.json
  annotations/<document_id>/<annotation_id>.json
  reviews/<document_id>/<review_id>.json
  dataset-releases/<release_id>/split_manifest.json
  dataset-releases/<release_id>/manifest.json
```

All three per-document artifact types are content-addressed and immutable
(RFC 0012 §3.1) — writing the same ID twice with identical content is a
no-op; writing the same ID with *different* content is a bug (a hash
collision, or a caller computing the ID wrong) and raises rather than
silently overwriting, which is exactly the property §3.1 requires: "o
registro original... nunca é apagado nem reescrito".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from segmenter_dataset.schemas import (
    AnnotationRecord,
    DocumentRecord,
    ReleaseManifest,
    ReviewRecord,
)


if TYPE_CHECKING:
    from pathlib import Path


class ImmutabilityError(ValueError):
    """An attempt to write different content under an existing content-addressed ID."""


class SegmenterDatasetStore:
    """Read/write access to ``data/segmenter/`` (RFC 0012 §8)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.documents_dir = root / "documents"
        self.annotations_dir = root / "annotations"
        self.reviews_dir = root / "reviews"
        self.releases_dir = root / "dataset-releases"

    # -- documents ----------------------------------------------------

    def write_document(self, document: DocumentRecord) -> Path:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        path = self.documents_dir / f"{document.document_id}.json"
        _write_immutable(path, document)
        return path

    def read_document(self, document_id: str) -> DocumentRecord:
        path = self.documents_dir / f"{document_id}.json"
        return DocumentRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list_documents(self) -> list[DocumentRecord]:
        if not self.documents_dir.exists():
            return []
        return [
            DocumentRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.documents_dir.glob("*.json"))
        ]

    # -- annotations ----------------------------------------------------

    def write_annotation(self, annotation: AnnotationRecord) -> Path:
        doc_dir = self.annotations_dir / annotation.document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        path = doc_dir / f"{annotation.annotation_id}.json"
        _write_immutable(path, annotation)
        return path

    def list_annotations(self, document_id: str | None = None) -> list[AnnotationRecord]:
        if not self.annotations_dir.exists():
            return []
        pattern = f"{document_id}/*.json" if document_id else "*/*.json"
        return [
            AnnotationRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.annotations_dir.glob(pattern))
        ]

    # -- reviews ----------------------------------------------------

    def write_review(self, review: ReviewRecord) -> Path:
        doc_dir = self.reviews_dir / review.document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        path = doc_dir / f"{review.review_id}.json"
        _write_immutable(path, review)
        return path

    def list_reviews(self, document_id: str | None = None) -> list[ReviewRecord]:
        if not self.reviews_dir.exists():
            return []
        pattern = f"{document_id}/*.json" if document_id else "*/*.json"
        return [
            ReviewRecord.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.reviews_dir.glob(pattern))
        ]

    # -- releases ----------------------------------------------------

    def release_dir(self, release_id: str) -> Path:
        return self.releases_dir / release_id

    def write_release_manifest(self, manifest: ReleaseManifest) -> Path:
        """Write the final release manifest. Refuses to overwrite an existing release (§12)."""
        release_dir = self.release_dir(manifest.release_id)
        manifest_path = release_dir / "manifest.json"
        if manifest_path.exists():
            msg = (
                f"release {manifest.release_id!r} already exists at {manifest_path} — "
                "refusing to overwrite (RFC 0012 §12)"
            )
            raise ImmutabilityError(msg)
        release_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return manifest_path

    def read_release_manifest(self, release_id: str) -> ReleaseManifest:
        path = self.release_dir(release_id) / "manifest.json"
        return ReleaseManifest.model_validate_json(path.read_text(encoding="utf-8"))


def _write_immutable(path: Path, record: DocumentRecord | AnnotationRecord | ReviewRecord) -> None:
    payload = record.model_dump_json(indent=2)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != payload:
            msg = (
                f"content-addressed record at {path} already exists with different content — "
                "this should be impossible unless the ID was computed incorrectly (RFC 0012 §3.1)"
            )
            raise ImmutabilityError(msg)
        return
    path.write_text(payload, encoding="utf-8")
