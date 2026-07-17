from __future__ import annotations

from segmenter_dataset.ids import annotation_id, document_id, review_id
from segmenter_dataset.schemas import (
    AnnotationRecord,
    AnnotatorConfig,
    DocumentRecord,
    ExtractionInfo,
    GroupingInfo,
    Label,
    ReviewRecord,
    SourceInfo,
)


ONTOLOGY_VERSION = "segmenter-ontology-v8.0.0"


def make_document(
    *,
    text: str = "CABEÇALHO texto ementa RELATÓRIO fim.",
    tribunal: str = "TJRO",
    document_type: str = "sentenca",
    source_uri: str = "ia://item/doc-1",
    source_hash: str = "hash-1",
    normalized_process_number: str | None = None,
    source_process_id: str | None = None,
    document_family: str | None = None,
    parent_document_id: str | None = None,
) -> DocumentRecord:
    doc_id = document_id(source_system="tjro_juris", source_uri=source_uri, source_hash=source_hash)
    return DocumentRecord(
        document_id=doc_id,
        text=text,
        proposed_labels=[],
        source=SourceInfo(
            system="tjro_juris",
            tribunal=tribunal,
            document_type=document_type,
            source_uri=source_uri,
            source_hash=source_hash,
        ),
        extraction=ExtractionInfo(method="boundary_phrase_extractor", version="1"),
        grouping=GroupingInfo(
            normalized_process_number=normalized_process_number,
            source_process_id=source_process_id,
            document_family=document_family,
            parent_document_id=parent_document_id,
        ),
    )


def make_annotation(
    document: DocumentRecord,
    *,
    annotator_id: str = "annotator-a",
    model_family: str = "family-a",
    seeded_with: str = "none",
    completed_at: str = "2026-01-01T00:00:00Z",
    labels: list[Label] | None = None,
    covered_categories: tuple[str, ...] = ("cabecalho_inicio", "cabecalho_fim"),
    allowed_unmatched: dict[str, str] | None = None,
    ontology_version: str = ONTOLOGY_VERSION,
    annotation_method: str = "independent_full_read",
) -> AnnotationRecord:
    labels = labels if labels is not None else [Label(start=0, end=9, category="cabecalho_inicio")]
    allowed_unmatched = allowed_unmatched or {}
    config = AnnotatorConfig(
        model_family=model_family,
        guideline_version="g1",
        seeded_with=seeded_with,
    )
    ann_id = annotation_id(
        document_id=document.document_id,
        annotator_id=annotator_id,
        annotator_config=config.model_dump(),
        ontology_version=ontology_version,
        covered_categories=covered_categories,
        labels=[label.model_dump() for label in labels],
        allowed_unmatched=allowed_unmatched,
        completed_at=completed_at,
        annotation_method=annotation_method,
    )
    return AnnotationRecord(
        annotation_id=ann_id,
        document_id=document.document_id,
        annotator_id=annotator_id,
        annotator_config=config,
        ontology_version=ontology_version,
        covered_categories=covered_categories,
        labels=labels,
        allowed_unmatched=allowed_unmatched,
        completed_at=completed_at,
        annotation_method=annotation_method,
    )


def make_review(
    document: DocumentRecord,
    annotations: list[AnnotationRecord],
    *,
    status: str = "accepted",
    approved_at: str = "2026-01-02T00:00:00Z",
    final_labels: list[Label] | None = None,
    allowed_unmatched: dict[str, str] | None = None,
    reviewers: tuple[str, ...] = ("reviewer-a", "reviewer-b"),
    resolution: str = "agreement",
    notes: tuple[str, ...] = (),
) -> ReviewRecord:
    final_labels = final_labels if final_labels is not None else list(annotations[0].labels)
    allowed_unmatched = allowed_unmatched or {}
    input_ids = tuple(annotation.annotation_id for annotation in annotations)
    rev_id = review_id(
        document_id=document.document_id,
        input_annotation_ids=input_ids,
        status=status,
        final_labels=[label.model_dump() for label in final_labels],
        allowed_unmatched=allowed_unmatched,
        reviewers=reviewers,
        resolution=resolution,
        notes=notes,
        approved_at=approved_at,
    )
    return ReviewRecord(
        review_id=rev_id,
        document_id=document.document_id,
        input_annotation_ids=input_ids,
        status=status,
        final_labels=final_labels,
        allowed_unmatched=allowed_unmatched,
        reviewers=reviewers,
        resolution=resolution,
        notes=notes,
        approved_at=approved_at,
    )
