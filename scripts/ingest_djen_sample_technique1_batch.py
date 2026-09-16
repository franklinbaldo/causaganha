r"""Ingest a batch of Technique 1 (RFC 0012 §8/§9) LLM annotations for real,
multi-tribunal DJEN sample documents (#1050).

``scripts/ingest_juris_technique1_batch.py`` mints new ``DocumentRecord``s
too, but only from TJRO JURIS candidates (hardcoded ``tribunal="TJRO"``,
``source="tjro_juris"``). Every document in the store today came through
that path or through the historical TJRO migration
(``scripts/ingest_synthetic_segmenter_corpus.py``) — 61/61 documents are
TJRO. #1050 explicitly asks to "include multiple document templates/types
and... multiple tribunals/sources", and the RFC's own train/val/test ratios
(70/15/15) only clear the RFC 0012 §5 item 4 per-split floor (>=30 val,
>=30 test, both adjudicated) once the total corpus reaches roughly the
document count the RFC's own supply targets imply (150+30+30=210) — see
``docs/planning/evidence/segmenter-per-split-floor-ceiling-2026-09-16.json``.
Growing the corpus, not just adjudicating the existing 61-document pool, is
what raises that ceiling.

``data/segmenter_samples/*.jsonl`` already holds hundreds of real,
already-fetched full judicial texts from ~30 non-TJRO tribunals (one file
per tribunal/document-type combination), each carrying an ``info`` object
with tribunal/document-type/provenance metadata and a pre-computed
``cue_hits``/``cue_score`` triage (the same rare-category mining spirit as
:mod:`segmenter_dataset.candidate_mining`) — never ingested into the store.
This script is the "raw LLM tagged output -> ``AnnotationRecord``"
conversion tool for that pool, reusing every mechanical/fidelity check
``ingest_juris_technique1_batch`` already established rather than
re-inventing them, but deriving ``tribunal``/``document_type`` from each
candidate's own metadata instead of hardcoding TJRO.

Expects:

- ``--candidates``: a JSON file (list of objects), each with at least
  ``id_documento``, ``tribunal``, ``tipoDocumento`` (``"Sentença"`` or
  ``"Acórdão"`` — the only two document types the current v7/v8 guideline
  covers), ``texto_limpo``, and a ``source_item``/``source_json``/``sha256``
  provenance triple (shape produced by selecting real candidates out of
  ``data/segmenter_samples/*.jsonl``, e.g. via
  ``candidate_mining.mine_rare_category_candidates`` or the sample files'
  own ``cue_hits``).
- ``--tagged-dir``: a directory of ``<id_documento>.txt`` files, each
  holding one subagent's full Technique 1 tagged reproduction of the
  matching candidate's ``texto_limpo`` (canonical prompt:
  ``data/segmenter_splits/technique1_annotation_prompt.md``).
- ``--output``: the ``segmenter_dataset`` store root (e.g. ``data/segmenter``).

Only candidates with both a JSON entry and a tagged file are processed;
every other candidate is reported as not-yet-annotated, not an error. A
candidate whose ``tipoDocumento`` isn't ``Sentença``/``Acórdão`` is skipped
with a reason rather than guessed at — the guideline's document-type hint
only covers those two.

Every document is ingested train-only (one ``AnnotationRecord``, no
``ReviewRecord``), same scope decision as
``ingest_synthetic_segmenter_corpus``: this script has no second
independent annotation to pair with, so nothing here becomes val/test
eligible on its own — that still requires
``scripts/annotate_second_independent.py`` + ``scripts/adjudicate_segmenter_review.py``
per document, same as every other train-only document already in the store.

Usage::

    uv run python scripts/ingest_djen_sample_technique1_batch.py \\
        --candidates /path/to/djen_sample_candidates.json \\
        --tagged-dir /path/to/batch1_tagged \\
        --output data/segmenter
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from scripts.ingest_juris_technique1_batch import (
    _dedupe_single_anchor,
    _detect_allowed_unmatched,
    _drop_excluded_categories,
)
from segmenter_dataset.dedup import content_hash
from segmenter_dataset.ids import annotation_id as build_annotation_id
from segmenter_dataset.ids import document_id as build_document_id
from segmenter_dataset.mechanical import validate_record
from segmenter_dataset.ontology import ALLOW_MULTIPLE_SINGLE_ANCHOR, ONTOLOGY_V8, load_categories
from segmenter_dataset.schemas import (
    AnnotationRecord,
    AnnotatorConfig,
    DocumentRecord,
    ExtractionInfo,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore, _text_element_to_labels


SOURCE_SYSTEM = "djen_sample_technique1"
GUIDELINE_VERSION = "segmenter_v7.1"
MODEL_FAMILY = "prompt_subagents:general-purpose"
ANNOTATOR_ID = "llm_technique1:djen_sample_batch1"

# The guideline only ever asks a subagent to expect sentença- or
# acórdão-shaped structure (RFC 0012 §9's document_type_hint); other DJEN
# ``tipoDocumento`` values (e.g. "Decisão") have no vetted anchor
# expectations yet and are left out rather than guessed at.
_DOCUMENT_TYPE_MAP = {"Sentença": "sentenca", "Acórdão": "acordao"}


def _load_candidates(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["id_documento"]): item for item in data}


def _parse_tagged(tagged_text: str) -> tuple[str, list]:
    root = ET.fromstring(f"<text>{tagged_text.strip()}</text>")  # noqa: S314 -- own trusted batch dir
    return _text_element_to_labels(root)


def _build_annotation(
    document: DocumentRecord,
    labels: list,
    allowed_unmatched: dict[str, str],
    covered_categories: tuple[str, ...],
    *,
    completed_at: str,
) -> AnnotationRecord:
    annotator_config = AnnotatorConfig(
        model_family=MODEL_FAMILY,
        guideline_version=GUIDELINE_VERSION,
        seeded_with="none",
    )
    return AnnotationRecord(
        annotation_id=build_annotation_id(
            document_id=document.document_id,
            annotator_id=ANNOTATOR_ID,
            completed_at=completed_at,
            labels=[label.model_dump() for label in labels],
        ),
        document_id=document.document_id,
        annotator_id=ANNOTATOR_ID,
        annotator_config=annotator_config,
        ontology_version=ONTOLOGY_V8,
        covered_categories=covered_categories,
        labels=labels,
        allowed_unmatched=allowed_unmatched,
        completed_at=completed_at,
        annotation_method="independent_full_read",
    )


def ingest(
    candidates_path: Path,
    tagged_dir: Path,
    output_dir: Path,
    ontology_categories: set[str],
    *,
    completed_at: str,
) -> tuple[list[str], dict[str, str]]:
    """Returns (ingested doc_ids, {doc_id_key: skip_reason})."""
    store = SegmenterDatasetStore(output_dir)
    candidates = _load_candidates(candidates_path)
    ingested: list[str] = []
    skipped: dict[str, str] = {}

    for tagged_path in sorted(tagged_dir.glob("*.txt")):
        key = tagged_path.stem
        candidate = candidates.get(key)
        if candidate is None:
            skipped[key] = "no matching candidate metadata"
            continue

        document_type = _DOCUMENT_TYPE_MAP.get(candidate["tipoDocumento"])
        if document_type is None:
            skipped[key] = f"unsupported tipoDocumento {candidate['tipoDocumento']!r}"
            continue

        source_text = candidate["texto_limpo"]
        tagged_text = tagged_path.read_text(encoding="utf-8")

        try:
            reconstructed_text, labels = _parse_tagged(tagged_text)
        except ET.ParseError as exc:
            skipped[key] = f"malformed tagged XML: {exc}"
            continue

        if reconstructed_text != source_text:
            skipped[key] = (
                "verbatim-fidelity mismatch (RFC 0012 §9 risk signal, not auto-rejected "
                "here -- needs independent review before retry): reconstructed text "
                f"differs from source (len {len(reconstructed_text)} vs {len(source_text)})"
            )
            continue

        labels = _dedupe_single_anchor(_drop_excluded_categories(labels))
        allowed_unmatched = _detect_allowed_unmatched(labels)
        mechanical_problems = validate_record(
            source_text,
            labels,
            ontology_categories,
            allowed_unmatched=allowed_unmatched,
            allow_multiple_single_anchor=ALLOW_MULTIPLE_SINGLE_ANCHOR,
        )
        if mechanical_problems:
            skipped[key] = f"mechanical validation failed: {mechanical_problems}"
            continue

        source_uri = f"djen_sample_technique1:batch1:{candidate['tribunal']}:{key}"
        document = DocumentRecord(
            document_id=build_document_id(
                source_system=SOURCE_SYSTEM,
                source_uri=source_uri,
                source_hash=content_hash(source_text),
            ),
            text=source_text,
            source=SourceInfo(
                system=SOURCE_SYSTEM,
                tribunal=candidate["tribunal"],
                document_type=document_type,
                source_uri=source_uri,
                source_hash=content_hash(source_text),
            ),
            extraction=ExtractionInfo(
                method="llm_technique1_batch_annotation", version="djen_sample_batch1"
            ),
        )
        store.write_document(document)

        covered_categories = tuple(sorted(ontology_categories))
        annotation = _build_annotation(
            document, labels, allowed_unmatched, covered_categories, completed_at=completed_at
        )
        store.write_annotation(annotation)
        ingested.append(document.document_id)

    return ingested, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--tagged-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--label-space",
        type=Path,
        default=Path("data/segmenter_splits/label_space.json"),
    )
    parser.add_argument("--completed-at", type=str, required=True)
    args = parser.parse_args()

    ontology_categories = load_categories(args.label_space)
    ingested, skipped = ingest(
        args.candidates,
        args.tagged_dir,
        args.output,
        ontology_categories,
        completed_at=args.completed_at,
    )

    print(f"Ingested {len(ingested)} document(s):")
    for doc_id in ingested:
        print(f"  {doc_id}")
    if skipped:
        print(f"\nSkipped {len(skipped)} document(s):")
        for key, reason in skipped.items():
            print(f"  {key}: {reason}")


if __name__ == "__main__":
    main()
