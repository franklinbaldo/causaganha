"""Deterministic IDs for the segmenter dataset artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:32]}"


def document_id(*, source_system: str, source_uri: str, source_hash: str) -> str:
    """Stable source-addressed document identity.

    ``source_hash`` commits to the exact fetched bytes; extraction proposals are
    deliberately excluded so multiple extraction passes refer to one source document.
    """
    return _digest(
        "doc",
        {
            "source_system": source_system,
            "source_uri": source_uri,
            "source_hash": source_hash,
        },
    )


def annotation_id(
    *,
    document_id: str,
    annotator_id: str,
    annotator_config: dict[str, Any],
    ontology_version: str,
    covered_categories: list[str] | tuple[str, ...],
    labels: list[dict[str, Any]],
    allowed_unmatched: dict[str, str],
    completed_at: str,
    annotation_method: str,
) -> str:
    """Content-addressed annotation ID over every semantically relevant field."""
    return _digest(
        "ann",
        {
            "document_id": document_id,
            "annotator_id": annotator_id,
            "annotator_config": annotator_config,
            "ontology_version": ontology_version,
            "covered_categories": sorted(covered_categories),
            "labels": labels,
            "allowed_unmatched": allowed_unmatched,
            "completed_at": completed_at,
            "annotation_method": annotation_method,
        },
    )


def review_id(
    *,
    document_id: str,
    input_annotation_ids: list[str] | tuple[str, ...],
    status: str,
    final_labels: list[dict[str, Any]],
    allowed_unmatched: dict[str, str],
    reviewers: list[str] | tuple[str, ...],
    resolution: str,
    notes: list[str] | tuple[str, ...],
    approved_at: str,
) -> str:
    """Content-addressed review ID over the complete adjudication result."""
    return _digest(
        "rev",
        {
            "document_id": document_id,
            "input_annotation_ids": sorted(input_annotation_ids),
            "status": status,
            "final_labels": final_labels,
            "allowed_unmatched": allowed_unmatched,
            "reviewers": sorted(reviewers),
            "resolution": resolution,
            "notes": list(notes),
            "approved_at": approved_at,
        },
    )
