"""Test segmenter audit scripts."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

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


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def setup_dummy_store(tmp_path: Path) -> SegmenterDatasetStore:
    store = SegmenterDatasetStore(tmp_path / "store")

    document = DocumentRecord(
        document_id="doc_00000000000000000000000000000001",
        text="A B C D E F art. 1 art. 2 R$ 1 R$ 2 R$ 3 art. 3 art. 4",
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="acordao",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(document)

    annotator_config = AnnotatorConfig(
        model_family="test_model",
        guideline_version="test_v1",
    )
    annotation = AnnotationRecord(
        annotation_id="ann_00000000000000000000000000000001",
        document_id="doc_00000000000000000000000000000001",
        annotator_id="annotator1",
        annotator_config=annotator_config,
        ontology_version="test_v1",
        covered_categories=(
            "resultado",
            "relatorio_inicio",
            "relatorio_fim",
            "fundamentacao_legal",
        ),
        completed_at="2023-01-01T00:00:00Z",
        annotation_method="method1",
        labels=[
            Label(category="resultado", start=0, end=1),
            Label(category="relatorio_inicio", start=2, end=3),
            Label(category="relatorio_fim", start=4, end=5),
            Label(category="fundamentacao_legal", start=12, end=18),
        ],
    )
    store.write_annotation(annotation)
    return store


def test_compute_support(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    label_space_path = tmp_path / "label_space.json"
    label_space_path.write_text(
        json.dumps(
            {
                "span_class_names": [
                    "O",
                    "resultado",
                    "relatorio_inicio",
                    "relatorio_fim",
                    "fundamentacao_legal",
                ]
            }
        )
    )

    mod = load_script("segmenter_category_support", "scripts/segmenter_category_support.py")
    counts = mod.compute_support(tmp_path / "store", label_space_path)  # type: ignore[attr-defined]

    assert counts["resultado"] == 1
    assert counts["relatorio_inicio"] == 1
    assert counts["relatorio_fim"] == 1
    assert counts["fundamentacao_legal"] == 1


def test_compute_gaps(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    mod = load_script("segmenter_coverage_gap", "scripts/segmenter_coverage_gap.py")
    gaps = mod.compute_gaps(tmp_path / "store")  # type: ignore[attr-defined]

    bucket_key = "sys1|method1|annotator1"
    assert bucket_key in gaps
    assert gaps[bucket_key] == []


def test_find_anti_patterns(tmp_path: Path) -> None:
    setup_dummy_store(tmp_path)

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    doc_id = "doc_00000000000000000000000000000001"
    assert doc_id in findings
    assert any(f["type"] == "fundamentacao_legal_collapsed" for f in findings[doc_id])


def test_find_anti_patterns_ignores_superseded_annotation(tmp_path: Path) -> None:
    """A document repaired by a *newer* annotation must stop being flagged.

    ``release.py``'s ``_latest_annotation`` picks the most recent
    ``completed_at`` per document for training (RFC 0012 §10) — a
    superseded, already-fixed annotation is never what training actually
    consumes, so re-auditing it forever would make the audit useless as a
    repair-completion signal (issue #1050).
    """
    store = setup_dummy_store(tmp_path)
    doc_id = "doc_00000000000000000000000000000001"

    corrected = AnnotationRecord(
        annotation_id="ann_00000000000000000000000000000002",
        document_id=doc_id,
        annotator_id="annotator2",
        annotator_config=AnnotatorConfig(model_family="test_model", guideline_version="test_v1"),
        ontology_version="test_v1",
        covered_categories=(
            "resultado",
            "relatorio_inicio",
            "relatorio_fim",
            "fundamentacao_legal",
        ),
        completed_at="2023-01-02T00:00:00Z",
        annotation_method="method1",
        labels=[
            Label(category="resultado", start=0, end=1),
            Label(category="relatorio_inicio", start=2, end=3),
            Label(category="relatorio_fim", start=4, end=5),
            Label(category="fundamentacao_legal", start=12, end=18),
            Label(category="fundamentacao_legal", start=19, end=25),
        ],
    )
    store.write_annotation(corrected)

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    assert not any(f["type"] == "fundamentacao_legal_collapsed" for f in findings.get(doc_id, []))


def test_real_store_has_at_most_the_one_known_collapsed_false_positive() -> None:
    """Regression guard for issue #1050's 2026-09 audit repair.

    13 of the 14 documents the audit flagged as "collapsed" had genuinely
    missing anchors and were repaired with a superseding annotation
    (``scripts/repair_segmenter_semantic_audit_2026_09.py``). The 14th,
    ``doc_d61aecbf08b525a26f908f655285fe6c``, was reviewed and left as-is:
    its two extra ``R$`` mentions are the disputed cautelar-de-arresto
    target value, not a condemnation amount, so the single existing
    ``valor_condenacao`` tag is already correct and the heuristic's
    ``>2`` threshold is a known false positive there.

    ``doc_3cffd7961e9fc910f6ae628f5aaa6c40`` (RFC 0012 §9 scale-up,
    2026-09-15) is the same shape of false positive for
    ``fundamentacao_legal_collapsed``: its adjudicated annotation has one
    real ``fundamentacao_legal`` span (the CDC art. 42 restitution
    reasoning), while the rest of its "art."/"artigo" mentions sit in a
    TJRO "Dispositivos relevantes citados" bibliography list (CF art. 5º,
    CPC art. 373, CC arts. 398/406, plus jurisprudence) — genuinely
    ``ref_normativa`` citations, not reasoning phrases, and
    ``ref_normativa`` is excluded from the trainable label space
    (RFC 0012 §5, ``ontology.EXCLUDED_CATEGORIES``) so it never reaches the
    annotation the heuristic scans. The heuristic's ``>3`` threshold counts
    those excluded citations anyway.

    ``doc_f985597a64cc7b5ad06731c072915a7a`` (djen_sample batch4, TRF4,
    2026-09-16) is the identical shape of false positive: one real
    ``fundamentacao_legal`` span ("conforme art. 447 do CC") plus 3 further
    "art." mentions (CPC art. 886, CPC art. 903, CC art. 182) that were
    correctly tagged ``ref_normativa`` and therefore dropped from the
    stored annotation the same way, leaving the heuristic's raw text scan
    to count all 4 and flag a false collapse.

    ``doc_2a07306d88d1acebcdc0aff9958f7009`` (djen_sample batch7, TJRR,
    2026-09-16) is the same shape of false positive as
    ``doc_d61aecbf08b525a26f908f655285fe6c`` above, for
    ``valor_condenacao_collapsed``: the restitution amount (R$ 843,47) is
    genuinely mentioned 4 times before the dispositivo (case value R$
    2.450,30 once, then the same disputed tariff figure R$ 843,47 three
    times across the relatorio and fundamentacao narrative) before the
    single correct condemnation tag in the dispositivo -- one real
    ``valor_condenacao``, five raw "R$" occurrences, the heuristic's ``>2``
    threshold flags it anyway.

    ``doc_3b0be436ba6753185997c37b2b6b9765`` (djen_sample batch8, TJSE,
    2026-09-16) is the same shape of false positive again for
    ``fundamentacao_legal_collapsed``: this is a compact Turma Recursal
    ementa+acordao export where the EMENTA block enumerates several
    "ART." citations in its caps-lock keyword-abstract style (art. 373,
    II do CPC; art. 42, parágrafo único, do CDC) -- an ementa's citations
    are boundary content inside ``ementa_inicio``/``ementa_fim``, not
    reasoning prose, and the guideline never asks for per-citation tagging
    inside an ementa. The one real ``fundamentacao_legal`` span
    ("NOS TERMOS DO ART. 142, §2º, I DO RITJSE.") sits in the
    acordao_decisorio region; a second "ART. 55, 2ª PARTE, DA LEI
    9.099/95." citation was deliberately left untagged because it is
    identical, verbatim, to the acordao_decisorio's own ``_fim`` anchor
    text (tagging it twice would overlap two categories on the same span,
    the guideline's own anti-pattern). Four raw "art."/"ART." mentions,
    one real reasoning-authority tag -- the heuristic's ``>3`` threshold
    flags it anyway.

    ``doc_db852d2ad03c021f0ac411e3e5b63b60`` (djen_sample batch20, TRF2,
    2026-09-17) is the same shape of false positive again for
    ``fundamentacao_legal_collapsed``: a capa+ementa-estruturada acordao
    whose "Dispositivos relevantes citados" list bare-cites CF/1988 art.
    201 §9º, Lei nº 9.494/1997 art. 1º-F, and CPC art. 85 §3º/art. 300 --
    all correctly tagged ``ref_normativa`` and excluded from the
    trainable label space the same way as the other entries above. The
    one real ``fundamentacao_legal`` span ("conforme art. 85, §3º, do
    CPC") sits in the reasoning prose proper. Four raw "art." mentions,
    one real reasoning-authority tag -- the heuristic's ``>3`` threshold
    flags it anyway.

    If this test starts seeing *more* than these six findings, a new
    real omission was introduced and needs the same triage — repair it, or
    extend this allowlist with a documented reason, never silence the
    assertion.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(store_dir)  # type: ignore[attr-defined]

    collapsed_doc_ids = {
        doc_id
        for doc_id, doc_findings in findings.items()
        if any(f["type"].endswith("_collapsed") for f in doc_findings)
    }

    assert collapsed_doc_ids == {
        "doc_d61aecbf08b525a26f908f655285fe6c",
        "doc_3cffd7961e9fc910f6ae628f5aaa6c40",
        "doc_f985597a64cc7b5ad06731c072915a7a",
        "doc_2a07306d88d1acebcdc0aff9958f7009",
        "doc_3b0be436ba6753185997c37b2b6b9765",
        "doc_db852d2ad03c021f0ac411e3e5b63b60",
    }
