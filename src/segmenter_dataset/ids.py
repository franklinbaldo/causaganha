"""Deterministic, content-addressed IDs for the segmenter dataset lifecycle.

RFC 0012 §3.1, §8: a document/annotation/review is identified by the hash of
its own content, never by a counter. Two annotations with identical content
collapse to the same ``annotation_id``; any difference in label, annotator,
or timestamp produces a new ID, never overwriting the previous one — that is
what "a document is never promoted, only referenced by new records" (§3.1)
means at the ID-generation layer.
"""

from __future__ import annotations

import hashlib
import json


def _stable_json(value: object) -> str:
    """Canonical JSON encoding used as hash input — sorted keys, no whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def document_id(*, source_system: str, source_uri: str, source_hash: str) -> str:
    """Content-addressed ID for a document record (RFC 0012 §8).

    Derived only from source identity fields, never from ``text`` directly —
    ``source_hash`` already commits to the exact bytes fetched from the
    source system, and keeping the ID formula independent of ``text`` means
    re-extracting the same source document with a different heuristic
    extractor (different ``proposed_labels``) still resolves to the same
    ``document_id``, as RFC 0012 §3.1 requires (the document record is one
    artifact type; extraction method is a detail of it, not a new identity).
    """
    digest = hashlib.sha256(
        _stable_json(
            {
                "source_system": source_system,
                "source_uri": source_uri,
                "source_hash": source_hash,
            }
        ).encode("utf-8")
    ).hexdigest()
    return f"doc_{digest[:32]}"


def annotation_id(
    *,
    document_id: str,
    annotator_id: str,
    completed_at: str,
    labels: list[dict],
) -> str:
    """Content-addressed ID for an annotation record (RFC 0012 §8)."""
    digest = hashlib.sha256(
        _stable_json(
            {
                "document_id": document_id,
                "annotator_id": annotator_id,
                "completed_at": completed_at,
                "labels": labels,
            }
        ).encode("utf-8")
    ).hexdigest()
    return f"ann_{digest[:32]}"


def review_id(
    *,
    document_id: str,
    input_annotation_ids: list[str],
    approved_at: str,
) -> str:
    """Content-addressed ID for a review/adjudication record (RFC 0012 §8)."""
    digest = hashlib.sha256(
        _stable_json(
            {
                "document_id": document_id,
                "input_annotation_ids": sorted(input_annotation_ids),
                "approved_at": approved_at,
            }
        ).encode("utf-8")
    ).hexdigest()
    return f"rev_{digest[:32]}"
