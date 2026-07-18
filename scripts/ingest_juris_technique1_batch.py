r"""Ingest a batch of Technique 1 (RFC 0012 §8/§9) LLM annotations for real JURIS docs.

Each input is a *fresh* TJRO JURIS document (never previously ingested) plus one
subagent's inline-tagged reproduction of it, produced by spawning one subagent per
document with the prompt in ``data/segmenter_splits/technique1_annotation_prompt.md``
(the canonical Technique 1 prompt — do not improvise a new one per batch, see that
file's "Why it's shaped this way" for the failure mode that caused). The subagent
rewrites the document verbatim, wrapping each anchor span in an inline XML tag
(guideline ``data/segmenter_splits/annotation_guideline_v7.md``, Rule 6) instead of
reporting ``start``/``end`` integers. This script is the "raw LLM tagged output ->
``AnnotationRecord``" conversion tool that RFC 0012 §9/§11 requires to run a
verbatim-fidelity check before accepting the result — a mismatch (the duplication
failure mode found in the second annotation pilot) is a **risk signal**, not an
automatic rejection (§9, "Dados de treino"): this script logs it and skips the
document rather than raising, so one bad annotation doesn't block the rest of the
batch. Skipped documents need independent review before a retry is trusted.

Expects:

- ``--candidates``: a JSON file (list of objects) with at least
  ``id_documento``, ``nr_processo``, ``tipo``, ``classe``, ``orgao``, ``url_portal``,
  ``texto_limpo`` per candidate (shape produced by the JURIS-pool research step).
- ``--tagged-dir``: a directory of ``<id_documento>.txt`` files, each holding one
  subagent's full tagged reproduction of the matching candidate's ``texto_limpo``.
- ``--output``: the ``segmenter_dataset`` store root (e.g. ``data/segmenter``).

Only candidates with both a JSON entry and a tagged file are processed; every other
candidate is reported as not-yet-annotated, not an error.

Usage::

    uv run python scripts/ingest_juris_technique1_batch.py \\
        --candidates /path/to/candidates_full_text.json \\
        --tagged-dir /path/to/batch1_tagged \\
        --output data/segmenter
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

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
    GroupingInfo,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore, _text_element_to_labels


SOURCE_SYSTEM = "tjro_juris"
GUIDELINE_VERSION = "segmenter_v7.1"
MODEL_FAMILY = "prompt_subagents:general-purpose"
COMPLETED_AT = "2026-07-18T00:00:00Z"
ACORDAO_TIPOS = frozenset({"ACÓRDÃO", "ACORDAO"})
INICIO_SUFFIX = "_inicio"
FIM_SUFFIX = "_fim"

# The guideline still asks annotators to tag ref_normativa (useful context for
# a human/LLM reader), but it is excluded from ONTOLOGY_V8's trainable space
# (RFC 0001: regex pre-pass at inference) — same exclusion the historical
# migration script applies (scripts/ingest_synthetic_segmenter_corpus.py).
EXCLUDED_CATEGORIES = frozenset({"ref_normativa"})


def _load_candidates(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["id_documento"]): item for item in data}


def _normalized_process_number(nr_processo: str) -> str:
    return re.sub(r"\D", "", nr_processo)


def _parse_tagged(tagged_text: str) -> tuple[str, list]:
    root = ET.fromstring(f"<text>{tagged_text.strip()}</text>")  # noqa: S314 -- own trusted batch dir
    return _text_element_to_labels(root)


def _drop_excluded_categories(labels: list) -> list:
    return [label for label in labels if label.category not in EXCLUDED_CATEGORIES]


def _dedupe_single_anchor(labels: list) -> list:
    """Keep only the first occurrence of a repeating single-anchor category.

    RFC 0012 §5 point 7: categories in ``ALLOW_MULTIPLE_SINGLE_ANCHOR`` are
    exempt — a real decision legitimately cites the law more than once or
    states more than one genuinely distinct amount, and deduping those to
    "first occurrence" silently drops real signal (found via this exact
    batch — doc 18419937 cites two different articles for two different
    points, not the same one restated).
    """
    seen: set[str] = set()
    kept: list = []
    for label in sorted(labels, key=lambda label: label.start):
        is_paired = label.category.endswith(INICIO_SUFFIX) or label.category.endswith(FIM_SUFFIX)
        if not is_paired and label.category not in ALLOW_MULTIPLE_SINGLE_ANCHOR:
            if label.category in seen:
                continue
            seen.add(label.category)
        kept.append(label)
    return kept


def _detect_allowed_unmatched(labels: list) -> dict[str, str]:
    """Auto-generate a reason only for a dangling ``_inicio`` that is genuinely last.

    A base's ``_inicio`` count exceeding its ``_fim`` count by exactly one means
    one instance of that base is unclosed — but a bare count mismatch says
    nothing about *where* that instance sits. It is only excusable as "region
    extends to EOD" if the dangling instance really is the last thing labeled
    in the document: no other category's label starts after it. A dangling
    ``_inicio`` followed by other labeled sections is a real missing-``_fim``
    annotation defect, not a boundary case, and must not be silently excused.
    """
    bases_with_inicio: dict[str, list] = {}
    bases_with_fim: dict[str, int] = {}
    for label in labels:
        if label.category.endswith(INICIO_SUFFIX):
            base = label.category[: -len(INICIO_SUFFIX)]
            bases_with_inicio.setdefault(base, []).append(label)
        elif label.category.endswith(FIM_SUFFIX):
            base = label.category[: -len(FIM_SUFFIX)]
            bases_with_fim[base] = bases_with_fim.get(base, 0) + 1

    dangling_bases = {
        base: inicio_labels
        for base, inicio_labels in bases_with_inicio.items()
        if len(inicio_labels) - bases_with_fim.get(base, 0) == 1
    }
    if not dangling_bases:
        return {}

    last_start = max(label.start for label in labels)
    reason = "batch1: no closing cue present in source text (region extends to EOD)"
    return {
        base: reason
        for base, inicio_labels in dangling_bases.items()
        if max(label.start for label in inicio_labels) == last_start
    }


def ingest(
    candidates_path: Path, tagged_dir: Path, output_dir: Path, ontology_categories: set[str]
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
                "here — needs independent review before retry): reconstructed text "
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

        tipo = candidate["tipo"]
        document_type = "acordao" if tipo in ACORDAO_TIPOS else "sentenca"
        source_uri = f"juris_technique1_batch1:{key}"

        document = DocumentRecord(
            document_id=build_document_id(
                source_system=SOURCE_SYSTEM,
                source_uri=source_uri,
                source_hash=content_hash(source_text),
            ),
            text=source_text,
            source=SourceInfo(
                system=SOURCE_SYSTEM,
                tribunal="TJRO",
                document_type=document_type,
                source_uri=source_uri,
                source_hash=content_hash(source_text),
            ),
            extraction=ExtractionInfo(method="llm_technique1_batch_annotation", version="batch1"),
            grouping=GroupingInfo(
                normalized_process_number=_normalized_process_number(candidate["nr_processo"]),
                source_process_id=candidate["nr_processo"],
            ),
        )
        store.write_document(document)

        covered_categories = tuple(sorted(ontology_categories))
        annotator_id = "llm_technique1:batch1"
        annotator_config = AnnotatorConfig(
            model_family=MODEL_FAMILY,
            guideline_version=GUIDELINE_VERSION,
            seeded_with="none",
        )
        annotation = AnnotationRecord(
            annotation_id=build_annotation_id(
                document_id=document.document_id,
                annotator_id=annotator_id,
                annotator_config=annotator_config.model_dump(),
                ontology_version=ONTOLOGY_V8,
                covered_categories=covered_categories,
                labels=[label.model_dump() for label in labels],
                allowed_unmatched=allowed_unmatched,
                completed_at=COMPLETED_AT,
                annotation_method="independent_full_read",
            ),
            document_id=document.document_id,
            annotator_id=annotator_id,
            annotator_config=annotator_config,
            ontology_version=ONTOLOGY_V8,
            covered_categories=covered_categories,
            labels=labels,
            allowed_unmatched=allowed_unmatched,
            completed_at=COMPLETED_AT,
            annotation_method="independent_full_read",
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
    args = parser.parse_args()

    ontology_categories = load_categories(args.label_space)
    ingested, skipped = ingest(args.candidates, args.tagged_dir, args.output, ontology_categories)

    print(f"Ingested {len(ingested)} document(s):")
    for doc_id in ingested:
        print(f"  {doc_id}")
    if skipped:
        print(f"\nSkipped {len(skipped)} document(s):")
        for key, reason in skipped.items():
            print(f"  {key}: {reason}")


if __name__ == "__main__":
    main()
