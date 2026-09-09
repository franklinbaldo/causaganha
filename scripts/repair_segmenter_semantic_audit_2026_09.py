"""One-time repair for the 2026-09 semantic audit findings (issue #1050).

``scripts/segmenter_semantic_audit.py`` flagged 14 real documents where
``fundamentacao_legal``/``valor_condenacao`` had only one anchor tagged even
though the source text plainly cites several distinct statutes/amounts —
exactly the "collapsed" omission `annotation_guideline_v7.md` §"Rule 1"
warns against (tag *every* distinct occurrence, not just the first).

Each repaired document gets a new, superseding ``AnnotationRecord`` (never
an in-place edit — RFC 0012 §3.1 immutability) whose ``completed_at`` is
later than the flawed one, so ``release.py``'s ``_latest_annotation``
picks it for any future train split. The original flawed record is left
exactly as written, for audit history.

One flagged document, ``doc_d61aecbf08b525a26f908f655285fe6c``, is
deliberately *not* repaired here: its two extra ``R$`` mentions are the
disputed cautelar-de-arresto target value, not a condemnation amount, so
the single existing tag is already correct and the heuristic's ``>2``
threshold is a false positive for this document — see
``scripts/segmenter_semantic_audit.py``'s own docstring note in this
script's final report.
"""

from __future__ import annotations

import json
from pathlib import Path

from segmenter_dataset.ids import annotation_id
from segmenter_dataset.mechanical import validate_record
from segmenter_dataset.ontology import ALLOW_MULTIPLE_SINGLE_ANCHOR, ONTOLOGY_V8
from segmenter_dataset.schemas import AnnotationRecord, AnnotatorConfig, Label
from segmenter_dataset.store import SegmenterDatasetStore


COMPLETED_AT = "2026-09-09T07:30:00Z"
ANNOTATOR_ID = "agent_repair:semantic_audit_2026_09"
ANNOTATOR_CONFIG = AnnotatorConfig(
    model_family="claude_agent_repair",
    guideline_version="segmenter_v7",
    seeded_with="semantic_audit_missing_anchor_repair",
)
ANNOTATION_METHOD = "semantic_audit_missing_anchor_repair"

# Each entry: (category, context, target). ``context`` must occur exactly
# once in the document text; ``target`` (also required to occur exactly
# once inside ``context``) is the actual span tagged. When the anchor text
# itself is unambiguous, ``target`` is ``None`` and the whole ``context``
# is tagged.
Addition = tuple[str, str, str | None]

REPAIRS: dict[str, list[Addition]] = {
    "doc_0705044238c01d27000e67b6c6f84a6b": [
        ("fundamentacao_legal", "art. 840 do Código Civil", None),
        (
            "fundamentacao_legal",
            'nos termos do art. 487, I e III, "b" do Código de Processo Civil',
            None,
        ),
        ("fundamentacao_legal", "art. 515, II, do referido diploma legal", None),
        ("fundamentacao_legal", "art. 1.000 do CPC", None),
    ],
    "doc_2239c33a0e57dea3ba4d1759e941be88": [
        ("fundamentacao_legal", "art. 8º, inc. III da CF/88", None),
        ("fundamentacao_legal", "art. 14 da Lei n. 3.896/2016", None),
    ],
    "doc_254a21481f0881a28220cd162f7e0c6a": [
        ("fundamentacao_legal", "artigo 38 da Lei 9.099/95", None),
        ("fundamentacao_legal", "485, IV do CPC", None),
        # "artigo 55, da Lei 9.099/95" is skipped: it is already the exact
        # span of the existing `custas_fim` closing cue, so tagging it here
        # too would overlap that anchor (RFC 0012 §11 forbids any two
        # label spans overlapping, regardless of category).
    ],
    "doc_3cffd7961e9fc910f6ae628f5aaa6c40": [
        ("fundamentacao_legal", "CPC, art. 373", None),
        ("fundamentacao_legal", "CC, arts. 398 e 406", None),
        ("fundamentacao_legal", "CF/1988, art. 5º, XVII e XX", None),
    ],
    "doc_3d2eb37d242cfb5ebad884e0d1dd109e": [
        # "art. 38, LF 9.099/95" and "artigos 54 e 55 da Lei n. 9.099/95" are
        # skipped: they sit entirely inside the existing `relatorio_inicio`
        # and `custas_fim` anchor spans respectively, so a separate
        # fundamentacao_legal tag there would overlap (RFC 0012 §11).
        ("fundamentacao_legal", "art. 337, § 3º e 4º do CPC", None),
    ],
    "doc_5aebeae7f0c99f1d7e25e14266dffd8f": [
        (
            "fundamentacao_legal",
            "do delito previsto no artigo 155, caput, do Código Penal",
            "artigo 155, caput, do Código Penal",
        ),
        (
            "fundamentacao_legal",
            "com fundamento no artigo 386, inciso VII do Código de Processo Penal",
            None,
        ),
    ],
    "doc_8dfe37bb8f3a6d0990cf1a74329f4d1a": [
        ("fundamentacao_legal", "art. 90, § 3º, do CPC", None),
        # "art. 90, § 2º, do Código de Processo Civil" is skipped: its tail
        # ("do Código de Processo Civil.") is already the existing
        # `custas_fim` closing-cue span, so a separate tag here would
        # overlap it (RFC 0012 §11).
        ("fundamentacao_legal", "art. 1.000, parágrafo único, CPC", None),
    ],
    "doc_9c45d216d09c12dbe0b743e0cff5f139": [
        (
            "fundamentacao_legal",
            "arts. 353 e 354 do CPC c/c art. 355, I também do CPC",
            None,
        ),
        ("fundamentacao_legal", "art. 840 do CC", None),
        ("fundamentacao_legal", "art. 1.000, CPC", None),
    ],
    "doc_bed363d93062300e16c05c0627d9ac01": [
        ("fundamentacao_legal", "art. 90, § 3º, do CPC", None),
        # "art. 90, § 2º, do Código de Processo Civil" is skipped: its tail
        # overlaps the existing `custas_fim` closing-cue span (same
        # pattern as doc_8dfe37bb8f3a6d0990cf1a74329f4d1a above).
        ("fundamentacao_legal", "art. 1.000, do CPC", None),
    ],
    "doc_caaead3cfab9d30deb02c4470bca1274": [
        ("fundamentacao_legal", "art. 355, I, do CPC", None),
        ("fundamentacao_legal", "artigos 42, caput e 59 da Lei 8.213/91", None),
    ],
    "doc_f22271af51fd1d9e2e0f296aea1b9617": [
        ("fundamentacao_legal", "art. 840 do Código Civil", None),
        (
            "fundamentacao_legal",
            'nos termos do art. 487, inc. I e III, alínea "b" do Código de Processo Civil',
            None,
        ),
        ("fundamentacao_legal", "art. 515, II, do referido diploma legal", None),
        ("fundamentacao_legal", "art. 1.000, do CPC", None),
    ],
    "doc_10e986e30b77e39227ea3d170755b70a": [
        (
            "valor_condenacao",
            "conserto do seu eletrodoméstico no valor de R$ 1.450,00",
            "R$ 1.450,00",
        ),
        (
            "valor_condenacao",
            "do conserto no valor de R$ 1.450,00 (um mil, quatrocentos e cinquenta reais), comprovado",
            "R$ 1.450,00",
        ),
    ],
    "doc_ee4b584da334febe688125e8d9ad909e": [
        (
            "valor_condenacao",
            "Condeno o requerido ao pagamento da quantia de R$ 5.000,00",
            "R$ 5.000,00",
        ),
    ],
    # doc_d61aecbf08b525a26f908f655285fe6c: reviewed, not repaired — see module docstring.
}


def _resolve_span(text: str, context: str, target: str | None) -> tuple[int, int]:
    occurrences = text.count(context)
    if occurrences != 1:
        message = f"expected exactly one occurrence of {context!r}, found {occurrences}"
        raise ValueError(message)
    context_start = text.index(context)
    if target is None:
        return context_start, context_start + len(context)
    local_occurrences = context.count(target)
    if local_occurrences != 1:
        message = f"expected exactly one occurrence of {target!r} inside context, found {local_occurrences}"
        raise ValueError(message)
    local_start = context.index(target)
    start = context_start + local_start
    return start, start + len(target)


def repair(store_dir: Path, *, label_space_path: Path) -> list[str]:
    store = SegmenterDatasetStore(store_dir)
    ontology_categories = set(json.loads(label_space_path.read_text())["span_class_names"]) - {"O"}

    written: list[str] = []
    for document_id, additions in REPAIRS.items():
        document = store.read_document(document_id)
        # Base off the original (earliest) annotation, not any already-written
        # repair from a previous run of this script — re-running must stay
        # idempotent (RFC 0012 §3.1: same ID + same content is a no-op).
        old_annotation = min(
            store.list_annotations(document_id=document_id), key=lambda a: a.completed_at
        )

        new_labels = list(old_annotation.labels)
        for category, context, target in additions:
            start, end = _resolve_span(document.text, context, target)
            new_labels.append(Label(start=start, end=end, category=category))

        problems = validate_record(
            document.text,
            new_labels,
            ontology_categories,
            allowed_unmatched=old_annotation.allowed_unmatched,
            declared_unmatched=bool(old_annotation.allowed_unmatched),
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
            covered_categories=old_annotation.covered_categories,
            labels=new_labels,
            allowed_unmatched=old_annotation.allowed_unmatched,
            completed_at=COMPLETED_AT,
            annotation_method=ANNOTATION_METHOD,
        )
        store.write_annotation(annotation)
        written.append(new_id)

    return written


def main() -> None:
    written = repair(
        Path("data/segmenter"), label_space_path=Path("data/segmenter_splits/label_space.json")
    )
    print(f"Wrote {len(written)} superseding annotations:")
    for ann_id in written:
        print(f"  {ann_id}")


if __name__ == "__main__":
    main()
