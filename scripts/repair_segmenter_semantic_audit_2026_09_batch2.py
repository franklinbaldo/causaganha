"""Second repair pass for ``segmenter_semantic_audit.py`` findings (issue #1050).

The first pass (``repair_segmenter_semantic_audit_2026_09.py``) fixed the
``_collapsed`` findings. This pass fixes two finding types that first pass
never touched and that no test asserted on until now, so they sat unrepaired
in the accepted gold corpus since 2026-09-15:

- ``long_anchor``: three ``acordao_decisorio_inicio`` anchors (127-202 chars)
  tagged the entire formulaic opening paragraph instead of a short cue.
  ``annotation_guideline_v7.md`` Rule 1 caps anchors at "~120 characters
  ... never a full paragraph", and the guideline's own worked example for
  this exact category is the short "Vistos, relatados e discutidos". Each
  is trimmed to "Vistos, relatados e discutidos estes autos" (the phrase
  common to all three documents, one word longer than the guideline's bare
  example for a clean sentence boundary) — the untagged remainder of the
  paragraph stays exactly as written, still inside the ``acordao_decisorio``
  wrapper region, per the guideline's "interior prose ... stays exactly as
  it was" rule.
- ``dispositivo_inside_voto``: one ``dispositivo_abertura`` ("Ante o
  exposto") tagged inside an individual judge's ``voto`` region in an
  acórdão — the guideline's own "Acórdão notes" anti-pattern: "do not also
  tag a single-judge dispositivo_abertura inside an individual voto ... An
  acórdão's operative result is the collegiate acordao_decisorio". The
  document's ``acordao_decisorio`` region had no ``resultado`` tag of its
  own (the actual operative result, "RECURSO NÃO CONHECIDO", was
  untagged); the misplaced ``dispositivo_abertura``/``resultado`` pair
  inside ``voto`` is removed and a single ``resultado`` tag is added on
  the collegiate operative phrase instead, matching the pattern already
  used by the sibling long-anchor documents above (e.g.
  ``doc_b0c364907d4409d67d4d2a734c7bd54d`` tags "NÃO CONHECIDO" as
  ``resultado`` inside its own ``acordao_decisorio``).

Each repaired document gets a new, superseding ``AnnotationRecord`` (never
an in-place edit — RFC 0012 §3.1 immutability) whose ``completed_at`` is
later than every existing annotation for that document, so
``release.py``'s ``_latest_annotation`` picks it for any future train
split. The original flawed records are left exactly as written, for audit
history.
"""

from __future__ import annotations

from pathlib import Path

from segmenter_dataset.ids import annotation_id
from segmenter_dataset.mechanical import validate_record
from segmenter_dataset.ontology import ALLOW_MULTIPLE_SINGLE_ANCHOR, ONTOLOGY_V8
from segmenter_dataset.schemas import AnnotationRecord, AnnotatorConfig, Label
from segmenter_dataset.store import SegmenterDatasetStore


COMPLETED_AT = "2026-09-24T18:00:00Z"
ANNOTATOR_ID = "agent_repair:semantic_audit_2026_09_batch2"
ANNOTATOR_CONFIG = AnnotatorConfig(
    model_family="claude_agent_repair",
    guideline_version="segmenter_v7",
    seeded_with="semantic_audit_long_anchor_and_dispositivo_in_voto_repair",
)
ANNOTATION_METHOD = "semantic_audit_long_anchor_and_dispositivo_in_voto_repair"

SHORT_ACORDAO_CUE = "Vistos, relatados e discutidos estes autos"

LONG_ANCHOR_DOCS = (
    "doc_b0c364907d4409d67d4d2a734c7bd54d",
    "doc_b8a4a405e45ffe9a1ab11cf902f849e2",
    "doc_c502b14fd24cd8133897a1863d25e30a",
)

DISPOSITIVO_INSIDE_VOTO_DOC = "doc_c772414481d672a6886be6f4f9d261c2"


def _trim_acordao_decisorio_inicio(document_text: str, labels: list[Label]) -> list[Label]:
    if document_text.count(SHORT_ACORDAO_CUE) != 1:
        message = f"expected exactly one occurrence of {SHORT_ACORDAO_CUE!r}"
        raise ValueError(message)
    start = document_text.index(SHORT_ACORDAO_CUE)
    end = start + len(SHORT_ACORDAO_CUE)

    trimmed = [label for label in labels if label.category != "acordao_decisorio_inicio"]
    if len(trimmed) != len(labels) - 1:
        message = "expected exactly one acordao_decisorio_inicio label to trim"
        raise ValueError(message)
    trimmed.append(Label(start=start, end=end, category="acordao_decisorio_inicio"))
    return trimmed


def _move_resultado_out_of_voto(document_text: str, labels: list[Label]) -> list[Label]:
    context = "RECURSO NÃO CONHECIDO"
    target = "NÃO CONHECIDO"
    if document_text.count(context) != 1:
        message = f"expected exactly one occurrence of {context!r}"
        raise ValueError(message)
    context_start = document_text.index(context)
    start = context_start + context.index(target)
    end = start + len(target)

    kept = [
        label for label in labels if label.category not in ("dispositivo_abertura", "resultado")
    ]
    if len(kept) != len(labels) - 2:
        message = "expected exactly one dispositivo_abertura and one resultado label to remove"
        raise ValueError(message)
    kept.append(Label(start=start, end=end, category="resultado"))
    return kept


def repair(store_dir: Path) -> list[str]:
    store = SegmenterDatasetStore(store_dir)

    written: list[str] = []
    for document_id in (*LONG_ANCHOR_DOCS, DISPOSITIVO_INSIDE_VOTO_DOC):
        document = store.read_document(document_id)
        # Base off the current latest annotation (not the earliest) --
        # that is the record the live audit actually flags and the one
        # ``release.py`` would resolve to for training; unlike the first
        # repair pass, there is no risk of clobbering an already-applied
        # fix here since these documents never had a later repair.
        latest_annotation = max(
            store.list_annotations(document_id=document_id), key=lambda a: a.completed_at
        )

        if document_id in LONG_ANCHOR_DOCS:
            new_labels = _trim_acordao_decisorio_inicio(
                document.text, list(latest_annotation.labels)
            )
        else:
            new_labels = _move_resultado_out_of_voto(document.text, list(latest_annotation.labels))

        problems = validate_record(
            document.text,
            new_labels,
            set(latest_annotation.covered_categories),
            allowed_unmatched=latest_annotation.allowed_unmatched,
            declared_unmatched=bool(latest_annotation.allowed_unmatched),
            allow_multiple_single_anchor=ALLOW_MULTIPLE_SINGLE_ANCHOR,
        )
        if problems:
            message = f"{document_id}: mechanical validation failed: {problems}"
            raise ValueError(message)

        labels_payload = [label.model_dump() for label in new_labels]
        new_id = annotation_id(
            document_id=document_id,
            annotator_id=ANNOTATOR_ID,
            completed_at=COMPLETED_AT,
            labels=labels_payload,
        )
        annotation = AnnotationRecord(
            annotation_id=new_id,
            document_id=document_id,
            annotator_id=ANNOTATOR_ID,
            annotator_config=ANNOTATOR_CONFIG,
            ontology_version=ONTOLOGY_V8,
            covered_categories=latest_annotation.covered_categories,
            labels=new_labels,
            allowed_unmatched=latest_annotation.allowed_unmatched,
            completed_at=COMPLETED_AT,
            annotation_method=ANNOTATION_METHOD,
        )
        store.write_annotation(annotation)
        written.append(new_id)

    return written


def main() -> None:
    written = repair(Path("data/segmenter"))
    print(f"Wrote {len(written)} superseding annotations:")
    for ann_id in written:
        print(f"  {ann_id}")


if __name__ == "__main__":
    main()
