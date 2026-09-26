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

    ``doc_3b0be436ba6753185997c37b2b6b9765`` (djen_sample batch8, TJSE)
    **was** the same shape of false positive for
    ``fundamentacao_legal_collapsed`` through round ``p08457`` (2026-09-26):
    its sole annotation at the time tagged only one of the two "ART."
    citations in the acordao_decisorio region as ``fundamentacao_legal``
    (the second, "ART. 55, 2ª PARTE, DA LEI 9.099/95.", was folded into
    the acordao_decisorio's own ``_fim`` anchor instead, to avoid
    double-tagging one span with two categories). Round ``kgxf50``
    (2026-09-26) added this document's second, independent annotation for
    issue #1051's val/test adjudication (RFC 0012 §9) -- ``_latest_per_document``
    now scans that *later* annotation, which tags both citations as
    distinct ``fundamentacao_legal`` spans (a legitimate, independent
    reading, not a defect), so the heuristic's raw "art." count no longer
    exceeds the tagged count and the false positive no longer reproduces.
    The accepted ``ReviewRecord`` adjudicating the two annotations kept
    the original single-tag structure (matching the reasoning above,
    since the two "ART." citations remain the same verbatim span as the
    acordao_decisorio close) -- only the *annotation-level* heuristic this
    script scans is affected, not the reviewed ground truth. Removed from
    this allowlist because it is no longer a live false positive, not
    because the underlying reasoning above stopped applying.

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

    ``doc_12f989ac213c5eadf857aacc69b33ad2`` (djen_sample batch22, TJTO,
    2026-09-19) is the same shape of false positive again for
    ``fundamentacao_legal_collapsed``: this sentença quotes an STJ
    precedent's ementa verbatim (REsp 1.804.804/MS, already covered by
    one ``ref_normativa`` tag on the citation itself) whose own numbered
    items cite "art. 278" (Lei 6.404/1976) and "art. 265" (CC), plus a
    literal transcription of Lei 11.101/2005 arts. 50/59 and CPC art. 584
    already covered by ``fundamentacao_legal``+``ref_normativa`` on the
    introductory sentence ("com fundamento no artigo 59..."). None of
    those quoted-block citations are this document's own
    reasoning-with-connector language, so they were correctly left
    untagged the same way ``ref_normativa`` citations are elsewhere in
    this allowlist. Seven raw "art." mentions, one real
    reasoning-authority tag -- the heuristic's ``>3`` threshold flags it
    anyway.

    If this test starts seeing *more* than these six findings, a new
    real omission was introduced and needs the same triage — repair it, or
    extend this allowlist with a documented reason, never silence the
    assertion. A document dropping OUT of this set (as
    ``doc_3b0be436ba6753185997c37b2b6b9765`` did in round ``kgxf50``) is
    fine and expected once a later, independent second annotation exists
    for it — shrink the set and document why, per the note above.
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
        "doc_db852d2ad03c021f0ac411e3e5b63b60",
        "doc_12f989ac213c5eadf857aacc69b33ad2",
    }


def test_find_anti_patterns_detects_operative_on_reasoning_or_verb(tmp_path: Path) -> None:
    """Unit coverage for a finding type never exercised by a synthetic fixture.

    Only ``fundamentacao_legal_collapsed`` had a controlled (non-real-corpus)
    test before this — ``operative_on_reasoning_or_verb``,
    ``capitulo_merito_on_prose``, ``ref_processual_mismatch`` and
    ``ref_normativa_overlap`` were only ever exercised implicitly by running
    the heuristic against whatever the real corpus happened to contain, so a
    latent bug in any of them could hide for as long as no real document
    triggered it (see the sibling tests below, and
    ``test_find_anti_patterns_detects_ref_normativa_overlap`` in particular).
    """
    store = SegmenterDatasetStore(tmp_path / "store")
    text = "Relatório. Isto posto, decido pela procedência do pedido. Fim."
    doc = DocumentRecord(
        document_id="doc_00000000000000000000000000000010",
        text=text,
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="sentenca",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(doc)
    start = text.index("decido")
    end = start + len("decido pela procedência do pedido")
    store.write_annotation(
        AnnotationRecord(
            annotation_id="ann_00000000000000000000000000000010",
            document_id=doc.document_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("dispositivo_abertura",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="dispositivo_abertura", start=start, end=end)],
        )
    )

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    assert any(f["type"] == "operative_on_reasoning_or_verb" for f in findings[doc.document_id])


def test_find_anti_patterns_detects_capitulo_merito_on_prose(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    text = "Capítulo do mérito.\nAnalisando os autos, verifico que o pedido procede integralmente."
    doc = DocumentRecord(
        document_id="doc_00000000000000000000000000000011",
        text=text,
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="sentenca",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(doc)
    store.write_annotation(
        AnnotationRecord(
            annotation_id="ann_00000000000000000000000000000011",
            document_id=doc.document_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("capitulo_merito_inicio",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="capitulo_merito_inicio", start=0, end=len(text))],
        )
    )

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    assert any(f["type"] == "capitulo_merito_on_prose" for f in findings[doc.document_id])


def test_find_anti_patterns_detects_ref_processual_mismatch(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    text = "Processo n. 9999999-99.2099.8.22.9999 referente aos autos originais."
    doc = DocumentRecord(
        document_id="doc_00000000000000000000000000000012",
        text=text,
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="sentenca",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(doc)
    start = text.index("9999999")
    end = start + len("9999999-99.2099.8.22.9999")
    store.write_annotation(
        AnnotationRecord(
            annotation_id="ann_00000000000000000000000000000012",
            document_id=doc.document_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("ref_processual",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="ref_processual", start=start, end=end)],
        )
    )

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    assert any(f["type"] == "ref_processual_mismatch" for f in findings[doc.document_id])


def test_find_anti_patterns_detects_ref_normativa_overlap(tmp_path: Path) -> None:
    """Regression test for a real detector bug found while auditing issue #1050.

    The real store always serializes each label with an ``ord="N"``
    attribute (``store.py``'s ``_labels_to_text_element``/``_render_item``),
    so a rendered span is always e.g. ``<ref_normativa ord="1">...`` — never
    the bare ``<ref_normativa>`` the old heuristic searched for with a plain
    substring check (``"<ref_normativa>" in xml_text``) and a matching
    non-attribute regex. That substring therefore never occurs in any real
    annotation file, making ``ref_normativa_overlap`` structurally dead code:
    it could never fire against the actual corpus regardless of whether a
    genuine ``ref_normativa``/``fundamentacao_legal`` overlap existed,
    silently defeating the exact check issue #1050 relies on to keep those
    two categories from ever conflating a bare citation with a citation used
    as this document's own reasoning.

    Fixed by matching the tag name with a word boundary and an optional
    attribute list (``<ref_normativa\\b[^>]*>``), which matches both the
    attribute-carrying real form and the bare form this test's fixture would
    also produce if the store ever stopped rendering ``ord``.
    """
    store = SegmenterDatasetStore(tmp_path / "store")
    text = "Aplica-se o art. 5 da Lei X conforme fundamentação explícita do juízo sobre o caso."
    doc = DocumentRecord(
        document_id="doc_00000000000000000000000000000013",
        text=text,
        source=SourceInfo(
            system="sys1",
            tribunal="trib1",
            document_type="sentenca",
            source_uri="uri1",
            source_hash="hash1",
        ),
        extraction=ExtractionInfo(method="method1", version="v1"),
        grouping=GroupingInfo(source_process_id="1234567-89.2023.8.22.0001"),
    )
    store.write_document(doc)
    rn_start = text.index("art. 5")
    rn_end = rn_start + len("art. 5 da Lei X")
    store.write_annotation(
        AnnotationRecord(
            annotation_id="ann_00000000000000000000000000000013",
            document_id=doc.document_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("fundamentacao_legal", "ref_normativa"),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[
                Label(category="fundamentacao_legal", start=0, end=len(text)),
                Label(category="ref_normativa", start=rn_start, end=rn_end),
            ],
        )
    )

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(tmp_path / "store")  # type: ignore[attr-defined]

    assert any(f["type"] == "ref_normativa_overlap" for f in findings[doc.document_id])


def test_real_store_has_no_operative_capitulo_processual_or_normativa_findings() -> None:
    """Regression guard closing the last blind spot flagged by issue #1050's audit.

    ``test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings``
    closed two of the six previously-unasserted finding types;
    ``operative_on_reasoning_or_verb``, ``capitulo_merito_on_prose`` and
    ``ref_processual_mismatch`` were the remaining three that heuristic ever
    computed but no test read, and ``ref_normativa_overlap`` was outright
    dead code (see ``test_find_anti_patterns_detects_ref_normativa_overlap``)
    until this round's fix. Live re-run against the real corpus after the
    fix reports zero findings of any of these four types — the fix closes a
    real detection gap without surfacing a backlog of undetected defects.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(store_dir)  # type: ignore[attr-defined]

    bad_types = {
        "operative_on_reasoning_or_verb",
        "capitulo_merito_on_prose",
        "ref_processual_mismatch",
        "ref_normativa_overlap",
    }
    offending = {
        doc_id: sorted(f["type"] for f in doc_findings if f["type"] in bad_types)
        for doc_id, doc_findings in findings.items()
        if any(f["type"] in bad_types for f in doc_findings)
    }
    assert offending == {}


def test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings() -> None:
    """Regression guard for issue #1050's 2026-09 semantic audit, second pass.

    Unlike the ``_collapsed`` types asserted above, ``long_anchor`` and
    ``dispositivo_inside_voto`` were never asserted on by any test, so they
    accumulated unrepaired in the accepted gold corpus since 2026-09-15:

    - Three ``acordao_decisorio_inicio`` anchors (127-202 chars) tagged the
      entire formulaic opening paragraph instead of a short cue —
      ``annotation_guideline_v7.md`` Rule 1 caps anchors at "~120 characters
      ... never a full paragraph", and the guideline's own worked example
      for this exact category is the short "Vistos, relatados e
      discutidos".
    - One ``dispositivo_abertura`` ("Ante o exposto") was tagged inside an
      individual judge's ``voto`` region in an acórdão — the guideline's own
      "Acórdão notes" anti-pattern: "do not also tag a single-judge
      dispositivo_abertura inside an individual voto"; the document's real
      operative result is the collegiate ``acordao_decisorio``, which had no
      ``resultado`` tag of its own.

    Repaired by ``scripts/repair_segmenter_semantic_audit_2026_09_batch2.py``,
    which trims the three long anchors to the guideline's own short cue and
    moves the one misplaced ``resultado`` onto the collegiate operative
    phrase, removing the erroneous ``dispositivo_abertura``.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_semantic_audit", "scripts/segmenter_semantic_audit.py")
    findings = mod.find_anti_patterns(store_dir)  # type: ignore[attr-defined]

    bad_types = {"long_anchor", "dispositivo_inside_voto"}
    offending = {
        doc_id: sorted(f["type"] for f in doc_findings if f["type"] in bad_types)
        for doc_id, doc_findings in findings.items()
        if any(f["type"] in bad_types for f in doc_findings)
    }
    assert offending == {}
