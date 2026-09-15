r"""Ingest a genuinely independent second annotation for an existing document.

Unlike ``scripts/ingest_juris_technique1_batch.py`` (which mints a brand-new
``DocumentRecord`` per candidate), this script's target document already
exists in the segmenter dataset store (``data/segmenter/documents/``). It
exists to produce the **second** unseeded annotation a document needs before
``scripts/adjudicate_segmenter_review.py`` can adjudicate it into a
``ReviewRecord`` — the val/test eligibility gate RFC 0012 §10 requires
(#1050/#1051).

Independence (RFC 0012 §5.3) is a property of a *pair*, not of one
annotation in isolation, so this script does not check it — it only writes
an ``AnnotatorConfig`` with ``seeded_with="none"`` and whatever
``model_family`` the caller declares. Whether that forms an independent pair
with an existing annotation is checked where it matters: at review-write
time, by ``SegmenterDatasetStore.write_review``'s ``NonIndependentReviewError``
guard.

Expects a subagent's full tagged reproduction of the document (Técnica 1,
the canonical prompt in ``data/segmenter_splits/technique1_annotation_prompt.md``)
produced *without* the subagent seeing any existing annotation of the same
document — that independence of process, not just of stored metadata, is
what RFC 0012 §9 ("Dados de validação e teste") actually requires.

Usage::

    uv run python scripts/annotate_second_independent.py \
        --data-root data/segmenter \
        --document-id doc_57d1c65ce480854290dc81fd59d4827d \
        --tagged-file /path/to/second_annotation_tagged.txt \
        --annotator-id llm_technique1:second_independent_pilot \
        --model-family prompt_subagents:general-purpose \
        --completed-at 2026-09-15T08:40:00Z
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from segmenter_dataset.ids import annotation_id as build_annotation_id
from segmenter_dataset.mechanical import validate_record
from segmenter_dataset.ontology import ALLOW_MULTIPLE_SINGLE_ANCHOR, ONTOLOGY_V8, load_categories
from segmenter_dataset.schemas import AnnotationRecord, AnnotatorConfig, DocumentRecord
from segmenter_dataset.store import SegmenterDatasetStore, _text_element_to_labels


EXCLUDED_CATEGORIES = frozenset({"ref_normativa"})


class VerbatimFidelityError(ValueError):
    """The tagged reproduction, with tags stripped, doesn't match the stored document text."""


class MechanicalValidationError(ValueError):
    """The parsed labels fail RFC 0012 §11 mechanical validation."""


def _parse_tagged(tagged_text: str) -> tuple[str, list]:
    root = ET.fromstring(f"<text>{tagged_text.strip()}</text>")  # noqa: S314 -- own trusted subagent output, verified below
    return _text_element_to_labels(root)


def _drop_excluded_categories(labels: list) -> list:
    return [label for label in labels if label.category not in EXCLUDED_CATEGORIES]


def build_second_annotation(
    document: DocumentRecord,
    tagged_text: str,
    *,
    annotator_id: str,
    model_family: str,
    guideline_version: str,
    completed_at: str,
    ontology_categories: set[str],
    annotation_method: str = "independent_full_read",
    allowed_unmatched: dict[str, str] | None = None,
) -> AnnotationRecord:
    """Parse, verify, and package one subagent's independent tagged reproduction.

    Raises rather than skipping — unlike the batch ingestion script, this
    tool processes one document at a time, so a defect should stop the run
    and be visible, not vanish into a skip-reason dict meant for a batch.
    """
    reconstructed_text, labels = _parse_tagged(tagged_text)
    if reconstructed_text != document.text:
        message = (
            f"verbatim-fidelity mismatch for {document.document_id!r}: reconstructed text "
            f"differs from the stored document (len {len(reconstructed_text)} vs "
            f"{len(document.text)}) — RFC 0012 §9 risk signal, needs independent review "
            "before retry"
        )
        raise VerbatimFidelityError(message)

    labels = _drop_excluded_categories(labels)
    allowed_unmatched = allowed_unmatched or {}
    problems = validate_record(
        document.text,
        labels,
        ontology_categories,
        allowed_unmatched=allowed_unmatched,
        allow_multiple_single_anchor=ALLOW_MULTIPLE_SINGLE_ANCHOR,
    )
    if problems:
        message = f"mechanical validation failed for {document.document_id!r}: {problems}"
        raise MechanicalValidationError(message)

    annotator_config = AnnotatorConfig(
        model_family=model_family, guideline_version=guideline_version, seeded_with="none"
    )
    return AnnotationRecord(
        annotation_id=build_annotation_id(
            document_id=document.document_id,
            annotator_id=annotator_id,
            completed_at=completed_at,
            labels=[label.model_dump() for label in labels],
        ),
        document_id=document.document_id,
        annotator_id=annotator_id,
        annotator_config=annotator_config,
        ontology_version=ONTOLOGY_V8,
        covered_categories=tuple(sorted(ontology_categories)),
        labels=labels,
        allowed_unmatched=allowed_unmatched,
        completed_at=completed_at,
        annotation_method=annotation_method,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/segmenter"))
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--tagged-file", type=Path, required=True)
    parser.add_argument("--annotator-id", required=True)
    parser.add_argument("--model-family", required=True)
    parser.add_argument("--guideline-version", default="segmenter_v7")
    parser.add_argument("--completed-at", required=True)
    parser.add_argument("--annotation-method", default="independent_full_read")
    parser.add_argument("--allowed-unmatched", default="{}", help="JSON object, base -> reason")
    parser.add_argument(
        "--label-space", type=Path, default=Path("data/segmenter_splits/label_space.json")
    )
    args = parser.parse_args(argv)

    store = SegmenterDatasetStore(args.data_root)
    document = store.read_document(args.document_id)
    tagged_text = args.tagged_file.read_text(encoding="utf-8")
    ontology_categories = load_categories(args.label_space)

    annotation = build_second_annotation(
        document,
        tagged_text,
        annotator_id=args.annotator_id,
        model_family=args.model_family,
        guideline_version=args.guideline_version,
        completed_at=args.completed_at,
        ontology_categories=ontology_categories,
        annotation_method=args.annotation_method,
        allowed_unmatched=json.loads(args.allowed_unmatched),
    )
    store.write_annotation(annotation)
    print(f"Wrote annotation {annotation.annotation_id} for {document.document_id}")


if __name__ == "__main__":
    main()
