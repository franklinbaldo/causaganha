r"""Ingest the historical synthetic-segmenter/foundation corpus (RFC 0012 PR 2).

Migrates the 151 real TJRO documents assembled on ``synthetic-segmenter/foundation``
(never merged; PR #832's follow-on work) from its ``data/segmenter_splits/*.jsonl``
format into ``segmenter_dataset``'s content-addressed ``documents/``/``annotations/``
artifacts (RFC 0012 §8).

Scope decision (see RFC 0012 §18's "131 docs das rodadas A-F" / "seed de 20 docs"
disposition, and the PR 2 kickoff discussion): every document is ingested as
**train-only** (one ``AnnotationRecord``, never a ``ReviewRecord``). Nothing becomes
val/test-eligible in this pass. Two independent reasons:

1. RFC 0012's ``val_test_independently_adjudicated`` gate requires a review that
   references two real, distinct ``AnnotationRecord``s. Every non-seed document here
   is single-annotator (``info.verification_method in {None, "single_pass_subagent_or_llm",
   "model_assisted_correction_v1", "model_assisted_correction_v1_over_gemini"}``) — there
   is no second independent annotation to reference.
2. The original 20-doc seed's val/test subset *did* go through a genuine 4-role
   ensemble verification (``info.verified=True``, ``verification_method=
   "ensemble_4role_sonnet"``) — but only the final post-adjudication label set survived;
   the four roles' individual outputs (``role1.jsonl``, ``role3.jsonl``, ...) were
   working files, never committed (see ``verification_ensemble_v7.md`` at commit
   ``9ef9a6df``, which is the protocol spec, not the outputs). There is nothing to
   reference as a second independent annotation even for those six documents.

So this script produces a legitimate, audit-ready **train supply**, not a release —
``build_dataset_release`` will refuse to proceed until real independent val/test
annotation exists (a separate, later PR 2 step, RFC 0012 §9.1.1).

Field-mapping notes (source data is real but its own provenance is uneven):

- ``ref_normativa`` labels are dropped. It's in the *foundation* branch's own
  label space (added there for an unrelated OPF-training experiment,
  ``d229206f``) but excluded from RFC 0012's frozen ``ONTOLOGY_V8`` — see
  ``segmenter_dataset/ontology.py``'s module docstring and ``data/segmenter_splits/
  label_space.json`` on ``main`` (25 trainable categories, no ``ref_normativa``).
- Every kept label passes through ``covered_categories = ONTOLOGY_V8`` (the labeler
  always read the full guideline per document — Round E is the one exception that
  skipped re-labeling ``ref_normativa`` specifically, which we drop anyway).
- Single-anchor categories (``ref_processual``, ``valor_condenacao``,
  ``fundamentacao_legal`` — no ``_inicio``/``_fim`` pairing) that repeat in one
  document keep only their first occurrence by start offset. This is not a new
  policy invented for this script: PR #832's own Round B batch resolved an
  analogous conflict ("13 such conflicts were resolved deterministically by keeping
  the first-listed span and dropping the duplicate" — manifest.json ``notes``).
- Dangling ``_inicio`` without a matching ``_fim`` gets an auto-generated
  ``allowed_unmatched`` reason only when it is positionally last — no other
  category's label starts after it (see ``_detect_allowed_unmatched``) — genuine
  in historical court documents where a section runs to the end of the collected
  text. A dangling ``_inicio`` with labeled sections after it is a real
  missing-``_fim`` defect and is left for the mechanical-validation skip path,
  same as any other unmatched pair with no excuse.
- Five provenance buckets, keyed off ``info`` fields that happen to still
  distinguish them (see ``_classify`` below) — everything else about a document's
  round-by-round history (Rounds A/B/C/D specifically) was not preserved in the
  per-record ``info`` object, only in ``manifest.json``'s free-text ``notes``.
  ``source_hash`` is ``content_hash(text)`` for every bucket: none of them preserved
  the original fetched bytes, only extracted text.

Usage::

    uv run python scripts/ingest_synthetic_segmenter_corpus.py \\
        --source /path/to/exported/segmenter_splits \\
        --output data/segmenter
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    Label,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore


FOUNDATION_TIP_SHA = "31a6f7f8c80f614c8ae412951c6e64734e0077cf"
SEED_SOURCE_COMMIT_DATE = "2026-06-05T23:21:55Z"
ROUND_DATE = "2026-07-16T00:00:00Z"

EXCLUDED_CATEGORIES = frozenset({"ref_normativa"})
INICIO_SUFFIX = "_inicio"
FIM_SUFFIX = "_fim"
GUIDELINE_VERSION = "segmenter_v7"
ACORDAO_ONLY_CATEGORIES = frozenset(
    {"acordao_decisorio_inicio", "acordao_decisorio_fim", "voto_inicio", "voto_fim"}
)


def _load_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _classify(info: dict) -> str:
    """Bucket a record by the provenance fields that actually survived ingestion."""
    labeler = info.get("labeler")
    source = info.get("source") or info.get("source_zip")
    if labeler == "model_assisted_correction_v1_over_gemini":
        return "round_f"
    if labeler == "model_assisted_correction_v1":
        return "round_e"
    if source == "djen-2025-06-02-TJRO.zip":
        return "seed"
    if source == "tjro_juris" and "nr_processo" in info:
        return "juris_expansion"
    return "rounds_abcd_unattributed"


_BUCKET_META = {
    "seed": {
        "system": "internet_archive_djen_ocr",
        "model_family": "prompt_subagents:haiku",
        "seeded_with": "none",
        "completed_at": SEED_SOURCE_COMMIT_DATE,
    },
    "juris_expansion": {
        "system": "tjro_juris",
        "model_family": "prompt_subagents:general-purpose",
        "seeded_with": "none",
        "completed_at": ROUND_DATE,
    },
    "rounds_abcd_unattributed": {
        "system": "tjro_juris",
        "model_family": "historical_migration_unspecified",
        "seeded_with": "none",
        "completed_at": ROUND_DATE,
    },
    "round_e": {
        "system": "tjro_juris",
        "model_family": "model_assisted_correction_v1",
        "seeded_with": "model_draft_checkpoint_inference",
        "completed_at": ROUND_DATE,
    },
    "round_f": {
        "system": "tjro_juris",
        "model_family": "model_assisted_correction_v1_over_gemini",
        "seeded_with": "model_draft_gemini_2.5",
        "completed_at": ROUND_DATE,
    },
}


def _annotation_method(bucket: str, info: dict) -> str:
    if info.get("verified") is True and info.get("verification_method") == "ensemble_4role_sonnet":
        return "historical_migration_ensemble_verified_train_only"
    if bucket in ("round_e", "round_f"):
        return "historical_migration_model_assisted_correction"
    return "historical_migration_single_pass"


def _document_type(info: dict, labels: list[Label]) -> str:
    doc_type = info.get("doc_type")
    if doc_type:
        return doc_type
    categories = {label.category for label in labels}
    return "acordao" if categories & ACORDAO_ONLY_CATEGORIES else "sentenca"


def _source_uri(bucket: str, info: dict, text: str, split: str, index: int) -> str:
    doc_id = info.get("doc_id")
    if doc_id:
        return f"{bucket}:{doc_id}"
    record_id = info.get("id")
    if record_id:
        return f"{bucket}:{record_id}"
    return f"{bucket}:{split}:{index}:{content_hash(text)[:16]}"


def _dedupe_single_anchor(labels: list[Label]) -> list[Label]:
    """Keep only the first occurrence of a repeating single-anchor category.

    RFC 0012 §5 point 7: categories in ``ALLOW_MULTIPLE_SINGLE_ANCHOR`` are
    exempt — a real decision legitimately cites the law more than once or
    states more than one genuinely distinct amount, and deduping those to
    "first occurrence" silently drops real signal.
    """
    seen: set[str] = set()
    kept: list[Label] = []
    for label in sorted(labels, key=lambda label: label.start):
        is_paired = label.category.endswith(INICIO_SUFFIX) or label.category.endswith(FIM_SUFFIX)
        if not is_paired and label.category not in ALLOW_MULTIPLE_SINGLE_ANCHOR:
            if label.category in seen:
                continue
            seen.add(label.category)
        kept.append(label)
    return kept


def _detect_allowed_unmatched(labels: list[Label]) -> dict[str, str]:
    """Auto-generate a reason only for a dangling ``_inicio`` that is genuinely last.

    A base's ``_inicio`` count exceeding its ``_fim`` count by exactly one means
    one instance of that base is unclosed — but a bare count mismatch says
    nothing about *where* that instance sits. It is only excusable as "the
    section runs to the end of the collected text" if the dangling instance
    really is the last thing labeled in the document: no other category's
    label starts after it. A dangling ``_inicio`` followed by substantial text
    and further labeled sections is not a boundary case — it's a genuine
    missing-``_fim`` annotation defect, the same class of problem this
    migration already skips documents for elsewhere, and must not be
    silently excused here.
    """
    bases_with_inicio: dict[str, list[Label]] = {}
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
    reason = "historical migration: section runs to the end of the collected text"
    return {
        base: reason
        for base, inicio_labels in dangling_bases.items()
        if max(label.start for label in inicio_labels) == last_start
    }


def _build_document(
    *, bucket: str, info: dict, text: str, labels: list[Label], split: str, index: int
) -> DocumentRecord:
    meta = _BUCKET_META[bucket]
    return DocumentRecord(
        document_id=build_document_id(
            source_system=meta["system"],
            source_uri=_source_uri(bucket, info, text, split, index),
            source_hash=content_hash(text),
        ),
        text=text,
        source=SourceInfo(
            system=meta["system"],
            tribunal="TJRO",
            document_type=_document_type(info, labels),
            source_uri=_source_uri(bucket, info, text, split, index),
            source_hash=content_hash(text),
        ),
        extraction=ExtractionInfo(
            method="synthetic_segmenter_foundation_migration",
            version=FOUNDATION_TIP_SHA,
        ),
        grouping=GroupingInfo(source_process_id=info.get("nr_processo")),
    )


def _build_annotation(
    *,
    bucket: str,
    info: dict,
    document: DocumentRecord,
    labels: list[Label],
    covered_categories: tuple[str, ...],
) -> AnnotationRecord:
    meta = _BUCKET_META[bucket]
    annotator_id = f"historical_migration:{bucket}"
    allowed_unmatched = _detect_allowed_unmatched(labels)
    annotation_method = _annotation_method(bucket, info)
    annotator_config = AnnotatorConfig(
        model_family=meta["model_family"],
        guideline_version=GUIDELINE_VERSION,
        seeded_with=meta["seeded_with"],
    )
    return AnnotationRecord(
        annotation_id=build_annotation_id(
            document_id=document.document_id,
            annotator_id=annotator_id,
            annotator_config=annotator_config.model_dump(),
            ontology_version=ONTOLOGY_V8,
            covered_categories=covered_categories,
            labels=[label.model_dump() for label in labels],
            allowed_unmatched=allowed_unmatched,
            completed_at=meta["completed_at"],
            annotation_method=annotation_method,
        ),
        document_id=document.document_id,
        annotator_id=annotator_id,
        annotator_config=annotator_config,
        ontology_version=ONTOLOGY_V8,
        covered_categories=covered_categories,
        labels=labels,
        allowed_unmatched=allowed_unmatched,
        completed_at=meta["completed_at"],
        annotation_method=annotation_method,
    )


def ingest(
    source_dir: Path, output_dir: Path, ontology_categories: set[str]
) -> tuple[dict[str, int], list[str]]:
    """Ingest every record that passes mechanical validation; skip and report the rest.

    A handful of historical records have genuine pairing defects (an orphaned
    ``_fim`` with no ``_inicio``, or ``_fim`` preceding its own ``_inicio``) that
    :func:`_detect_allowed_unmatched` cannot safely paper over — these are real
    annotation-quality problems in the source corpus, not artifacts of this
    migration, so the affected documents are skipped rather than force-fitted.
    """
    store = SegmenterDatasetStore(output_dir)
    bucket_counts: dict[str, int] = {}
    problems: list[str] = []

    for split in ("train", "val", "test"):
        records = _load_jsonl(source_dir / f"{split}.jsonl")
        for index, record in enumerate(records):
            info = record.get("info", {})
            bucket = _classify(info)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

            raw_labels = [
                Label(**label)
                for label in record["label"]
                if label["category"] not in EXCLUDED_CATEGORIES
            ]
            labels = _dedupe_single_anchor(raw_labels)

            document = _build_document(
                bucket=bucket,
                info=info,
                text=record["text"],
                labels=labels,
                split=split,
                index=index,
            )
            covered_categories = tuple(sorted(ontology_categories))
            annotation = _build_annotation(
                bucket=bucket,
                info=info,
                document=document,
                labels=labels,
                covered_categories=covered_categories,
            )

            issues = validate_record(
                document.text,
                annotation.labels,
                ontology_categories,
                allowed_unmatched=annotation.allowed_unmatched,
                allow_multiple_single_anchor=ALLOW_MULTIPLE_SINGLE_ANCHOR,
            )
            if issues:
                location = f"{split}:{index} {bucket} {document.document_id}"
                problems.append(f"[{location}] {'; '.join(issues)}")
                bucket_counts[bucket] -= 1
                continue

            store.write_document(document)
            store.write_annotation(annotation)

    return bucket_counts, problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="dir with train/val/test.jsonl")
    parser.add_argument("--output", type=Path, required=True, help="segmenter_dataset store root")
    parser.add_argument(
        "--label-space",
        type=Path,
        default=Path("data/segmenter_splits/label_space.json"),
        help="ONTOLOGY_V8's canonical label_space.json (25 trainable categories)",
    )
    args = parser.parse_args()

    ontology_categories = load_categories(args.label_space)
    counts, problems = ingest(args.source, args.output, ontology_categories)
    total = sum(counts.values())
    print(f"ingested {total} documents as train-only annotations:")
    for bucket, count in sorted(counts.items()):
        print(f"  {bucket}: {count}")
    if problems:
        print(f"\nskipped {len(problems)} document(s) with genuine mechanical defects:")
        for problem in problems:
            print(f"  {problem}")


if __name__ == "__main__":
    main()
