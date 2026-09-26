"""Test the segmenter_dataset store governance status diagnostic (issue #1051).

``assign_splits`` (RFC 0012 §10) silently returns an empty val/test split
whenever the store has zero accepted :class:`ReviewRecord` objects — that is
correct behavior, not a bug (see ``EmptyEvalSplitError``'s docstring, which
only guards *starved* eligible groups, not a genuinely empty eligible set).
But nothing previously surfaced *that the store is in that state* without
someone running ``assign-splits`` by hand and reading stderr. This script
makes the gap a first-class, testable fact so future segmenter rounds don't
have to rediscover it.
"""

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
    ReviewRecord,
    SourceInfo,
)
from segmenter_dataset.store import SegmenterDatasetStore


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _write_document_and_annotation(store: SegmenterDatasetStore, doc_id: str, ann_id: str) -> None:
    store.write_document(
        DocumentRecord(
            document_id=doc_id,
            text="texto de exemplo",
            source=SourceInfo(
                system="sys1",
                tribunal="trib1",
                document_type="acordao",
                source_uri=f"uri-{doc_id}",
                source_hash=f"hash-{doc_id}",
            ),
            extraction=ExtractionInfo(method="method1", version="v1"),
            grouping=GroupingInfo(source_process_id=f"{doc_id}-process"),
        )
    )
    store.write_annotation(
        AnnotationRecord(
            annotation_id=ann_id,
            document_id=doc_id,
            annotator_id="annotator1",
            annotator_config=AnnotatorConfig(
                model_family="test_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("resultado",),
            completed_at="2023-01-01T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="resultado", start=0, end=1)],
        )
    )


def test_reports_zero_evaluation_eligible_when_store_has_no_reviews(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    _write_document_and_annotation(store, "doc_" + "1" * 32, "ann_" + "1" * 32)
    _write_document_and_annotation(store, "doc_" + "2" * 32, "ann_" + "2" * 32)

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    assert status["document_count"] == 2
    assert status["annotation_count"] == 2
    assert status["review_count"] == 0
    assert status["train_eligible_count"] == 2
    assert status["evaluation_eligible_count"] == 0
    assert status["blocked_on_reviews"] is True
    assert status["val_count"] == 0
    assert status["test_count"] == 0
    assert status["meets_rfc_0012_split_floor"] is False
    assert status["corpus_scale_blocks_floor"] is True


def test_val_test_ceiling_reflects_full_adjudication_of_current_corpus(tmp_path: Path) -> None:
    """RFC 0012 Sec 5 item 4's per-split floor (>=30 val, >=30 test) is a function of
    *total corpus size*, not just review coverage: assign_splits' val/test targets
    are `round(total_eligible * ratio)`, where total_eligible counts every annotated
    document, not only the reviewed ones. A store can have every single document
    adjudicated and still fall short of the floor if the corpus itself is too small
    -- that is the fact this diagnostic must surface (issue #1050 vs #1051)."""
    store = SegmenterDatasetStore(tmp_path / "store")
    doc_ids = [f"doc_{i:032x}" for i in range(4)]
    first_ann_ids = [f"ann_{i:032x}" for i in range(4)]
    for doc_id, ann_id in zip(doc_ids, first_ann_ids, strict=True):
        _write_document_and_annotation(store, doc_id, ann_id)

    # Adjudicate every single document in this tiny 4-document corpus.
    for i, (doc_id, first_ann_id) in enumerate(zip(doc_ids, first_ann_ids, strict=True)):
        second_ann_id = f"ann_{i + 100:032x}"
        store.write_annotation(
            AnnotationRecord(
                annotation_id=second_ann_id,
                document_id=doc_id,
                annotator_id="annotator2",
                annotator_config=AnnotatorConfig(
                    model_family="other_model", guideline_version="test_v1"
                ),
                ontology_version="test_v1",
                covered_categories=("resultado",),
                completed_at="2023-01-02T00:00:00Z",
                annotation_method="method1",
                labels=[Label(category="resultado", start=0, end=1)],
            )
        )
        store.write_review(
            ReviewRecord(
                review_id=f"rev_{i:032x}",
                document_id=doc_id,
                input_annotation_ids=(first_ann_id, second_ann_id),
                status="accepted",
                final_labels=[Label(category="resultado", start=0, end=1)],
                reviewers=("reviewer1", "reviewer2"),
                resolution="agreement",
                approved_at="2023-01-03T00:00:00Z",
            )
        )

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    # 100% adjudicated (4/4 documents) -- but the corpus itself is far too small.
    assert status["evaluation_eligible_count"] == 4
    assert status["val_count"] == status["val_ceiling_at_full_adjudication"]
    assert status["test_count"] == status["test_ceiling_at_full_adjudication"]
    assert status["val_count"] < 30
    assert status["test_count"] < 30
    assert status["meets_rfc_0012_split_floor"] is False
    assert status["corpus_scale_blocks_floor"] is True


def test_evaluation_eligible_count_reflects_accepted_reviews(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    doc_id = "doc_" + "3" * 32
    ann_id_1 = "ann_" + "3" * 32
    ann_id_2 = "ann_" + "4" * 32
    _write_document_and_annotation(store, doc_id, ann_id_1)
    store.write_annotation(
        AnnotationRecord(
            annotation_id=ann_id_2,
            document_id=doc_id,
            annotator_id="annotator2",
            annotator_config=AnnotatorConfig(
                model_family="other_model", guideline_version="test_v1"
            ),
            ontology_version="test_v1",
            covered_categories=("resultado",),
            completed_at="2023-01-02T00:00:00Z",
            annotation_method="method1",
            labels=[Label(category="resultado", start=0, end=1)],
        )
    )
    store.write_review(
        ReviewRecord(
            review_id="rev_" + "5" * 32,
            document_id=doc_id,
            input_annotation_ids=(ann_id_1, ann_id_2),
            status="accepted",
            final_labels=[Label(category="resultado", start=0, end=1)],
            reviewers=("reviewer1", "reviewer2"),
            resolution="agreement",
            approved_at="2023-01-03T00:00:00Z",
        )
    )

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(tmp_path / "store")  # type: ignore[attr-defined]

    assert status["review_count"] == 1
    assert status["evaluation_eligible_count"] == 1
    assert status["blocked_on_reviews"] is False


def test_real_store_has_at_least_one_evaluation_eligible_document() -> None:
    """Regression guard documenting #1051's first real, adjudicated review.

    Originally this test asserted ``review_count == 0`` /
    ``blocked_on_reviews is True`` — a snapshot of the store the day this
    diagnostic was introduced (61 documents, 74 annotations, zero
    ``ReviewRecord``s). That snapshot's own docstring already called for
    this update: "If this test starts seeing ``blocked_on_reviews is
    False``, #1051 has made real progress -- update/remove this regression
    guard instead of treating a flip here as a failure." It has: this store
    now carries the first accepted ``ReviewRecord``
    (``data/segmenter/reviews/doc_57d1c65ce480854290dc81fd59d4827d/``, built
    by ``scripts/adjudicate_segmenter_review.py`` from a second, genuinely
    independent annotation produced by ``scripts/annotate_second_independent.py``
    — see ``docs/planning/evidence/first-real-review-2026-09-15.json``), so
    ``assign-splits`` can produce a non-empty val/test manifest for the first
    time. #1051's remaining work is scaling this from 1 document to the
    RFC 0012 §5.4 targets (>= 30 val, >= 30 test adjudicated), not making the
    mechanism exist in the first place.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["document_count"] > 0
    assert status["review_count"] >= 1
    assert status["evaluation_eligible_count"] >= 1
    assert status["blocked_on_reviews"] is False

    # Former regression guard (introduced c4y4rc, asserted `corpus_scale_blocks_floor
    # is True` / `meets_rfc_0012_split_floor is False`): RFC 0012 Sec 5 item 4's
    # per-split floor (>=30 val, >=30 test, each adjudicated) is a function of
    # *total corpus size* (val_target = round(total_eligible * val_ratio)), not
    # just review coverage. That guard's own docstring called for this update:
    # "If this assertion ever starts failing because corpus_scale_blocks_floor is
    # False, issue #1050 (corpus scale-up) has made enough real progress to lift
    # this structural ceiling -- update/remove this guard instead of treating a
    # flip here as a failure." It has: Lote 28 (#1050, batch28) pushed
    # document_count from 195 to 197, and val_ceiling_at_full_adjudication /
    # test_ceiling_at_full_adjudication both reached 30 for the first time (see
    # test_real_store_reflects_batch28_corpus_growth). The corpus-size ceiling is
    # no longer the blocker; #1051's remaining work (scaling review_count from 32
    # towards the real, non-ceiling val/test counts of >=30/>=30) is now purely an
    # adjudication-coverage gap, not a structural one.
    assert status["corpus_scale_blocks_floor"] is False
    assert status["val_ceiling_at_full_adjudication"] >= 30
    assert status["test_ceiling_at_full_adjudication"] >= 30
    assert status["meets_rfc_0012_split_floor"] is False


def test_real_store_reflects_batch9_corpus_growth() -> None:
    """Regression guard for #1050 batch9 (2026-09-16, 6 docs: TJBA, TJMG,
    TJRS, TJSE, TRF2, TJCE -- see
    ``docs/planning/evidence/segmenter-djen-sample-batch8-2026-09-16.json``,
    named "batch8" in its evidence filename due to a numbering collision
    documented in ``knowledge/backlog/issue-1050.md``; the prose there
    numbers this round "lote 9" in the real historical sequence).

    Before this batch: document_count=109, val_ceiling=16, test_ceiling=16
    (last-verified live snapshot per ``knowledge/backlog/issue-1050.md``).
    After: document_count=115, val_ceiling=17, test_ceiling=17. RED before
    ingestion (109 < 115), GREEN after (this test only passes once the
    batch's 6 documents are actually present in the store) -- same
    RED->GREEN shape as every prior batch's regression guard in this file.

    If this test starts seeing a *lower* document_count than 115, a
    concurrent session's ingestion this file's own numbers were checked
    against was rolled back or the store was reset -- investigate before
    assuming this guard is simply stale (corpus size should only grow,
    never shrink, per #1050's whole premise). If it is genuinely stale
    because a later batch grew the corpus further, update the thresholds
    forward rather than deleting the guard.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["document_count"] >= 115
    assert status["val_ceiling_at_full_adjudication"] >= 17
    assert status["test_ceiling_at_full_adjudication"] >= 17


def test_real_store_reflects_batch10_corpus_growth() -> None:
    """Regression guard for #1050's tenth real DJEN sample batch.

    Snapshot before this batch: 109 documents (after batches 1-8 merged;
    a concurrent session's ninth batch, PR #1557, was still open with CI
    pending when this batch was selected and is merged separately as
    ``test_real_store_reflects_batch9_corpus_growth`` above). This batch
    adds two previously-unused real Sentença documents targeting the
    ``preliminar`` cue (still the scarcest category at 21 instances) from
    tribunals already represented but with only one document each:
    TJRN/72797727 (``source.source_hash`` prefix ``e9cd07f4``, i.e.
    ``segmenter_dataset.dedup.content_hash`` of the document's own text —
    not DJEN's own ``sha256`` field, a different hash space entirely, per
    knowledge/backlog/issue-1050.md's risk class 9) and TJBA/574460089
    (prefix ``d91719f4``). An initial selection of TJRN/72798564 and
    TJBA/574460090 was ingested and reverted mid-round after `git status`
    showed zero new ``documents/`` files — both had already been ingested
    by an earlier batch under the same (tribunal, id_documento) pair; see
    that risk class entry and this round's AgentDecision record. If corpus
    growth from a later concurrent batch changes the exact total, update
    the count here rather than treating a higher number as a failure — the
    two specific document hashes are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 117
    assert any(h.startswith("e9cd07f4") for h in hashes), "TJRN batch10 document missing"
    assert any(h.startswith("d91719f4") for h in hashes), "TJBA batch10 document missing"


def test_real_store_reflects_batch11_corpus_growth() -> None:
    """Regression guard for #1050's eleventh real DJEN sample batch.

    Snapshot before this batch: 117 documents (after batches 1-10 merged,
    confirmed live via ``scripts/segmenter_governance_status.py``). Unlike
    batches 6/7/10, no unused ``preliminar``-cue candidate remains in any
    already-represented tribunal (a fresh scan over every
    ``data/segmenter_samples/*.jsonl`` record, excluding every
    ``(tribunal, id_documento)`` pair already present in the store, found
    zero); this batch follows batch9's volume strategy instead, picking the
    two least-represented tribunals (both at ``store_count=2``) with a
    genuinely new, non-duplicate, markup-free candidate available: TJRN and
    TJMA. TJRN/72796443 (``source.source_hash`` prefix ``2ed02f57``) is a
    clean-text Sentença; TJMA/42728353 (prefix ``766e2846``) is a Sentença
    hitting ``acordao_decisorio``/``custas``/``honorarios``/``voto`` cues. A
    TST Acórdão candidate pair was scanned and rejected first: both
    ``237077355`` and ``237077375`` in ``tst_acordao.jsonl`` reproduce the
    identical judgment body for the same case
    (``TST-AIRR-0094800-39.1997.5.20.0003``), differing only in the
    ``Intimado(s)/Citado(s)`` footer party name -- ingesting both would pad
    ``document_count`` without adding real training diversity, the same
    anti-pattern the corpus-scale floor (RFC 0012 Sec 5 item 4) is meant to
    guard against. If corpus growth from a later concurrent batch changes
    the exact total, update the count here rather than treating a higher
    number as a failure -- the two specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 119
    assert any(h.startswith("2ed02f57") for h in hashes), "TJRN batch11 document missing"
    assert any(h.startswith("766e2846") for h in hashes), "TJMA batch11 document missing"


def test_real_store_reflects_batch12_corpus_growth() -> None:
    """Regression guard for #1050's twelfth real DJEN sample batch.

    Snapshot before this batch: 119 documents (after batches 1-11 merged,
    confirmed live via ``scripts/segmenter_governance_status.py``). A live
    scan of every ``data/segmenter_samples/*.jsonl`` record (excluding TJRO,
    filtering 2500-18000 chars, Sentenca/Acordao, deduped against the
    current store's ``source_uri``s) found TJES and TJGO tied for the
    lowest non-singleton ``store_count`` (2 each), each with a real unused
    Sentenca candidate carrying a ``preliminar`` rare-category cue:
    TJES/577054686 (clean text, no HTML entities) and TJGO/543562390 (364
    raw HTML entities in ``texto_limpo``, resolved with ``html.unescape()``
    before annotation -- the same fix batch2/batch7 established). Neither
    candidate's raw text contains embedded HTML markup (no ``<tag>``
    matches), so the batch3 HTML-to-text cleaner was not needed. If corpus
    growth from a later concurrent batch changes the exact total, update
    the count here rather than treating a higher number as a failure -- the
    two specific document hashes are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 121
    assert any(h.startswith("57ea4a68") for h in hashes), "TJES batch12 document missing"
    assert any(h.startswith("b04a0802") for h in hashes), "TJGO batch12 document missing"


def test_real_store_reflects_batch13_corpus_growth() -> None:
    """Regression guard for #1050's thirteenth real DJEN sample batch.

    Snapshot before this batch: 121 documents (after batches 1-12 merged,
    confirmed live via ``scripts/segmenter_governance_status.py``). A live
    scan of every ``data/segmenter_samples/*.jsonl`` record (excluding
    TJRO and the ``*_annotation_gold``/``*_annotation_raw`` auxiliary
    files, filtering 2500-18000 chars, Sentenca/Acordao, deduped against
    the current store's ``source_uri``s and ``source_hash``es) found eight
    tribunals tied at the lowest non-singleton ``store_count`` (2 each):
    TJPI, TJRJ, TJSE, TJMG, TRF5, TJRS, TRF2, TJTO. TJSE and TJRS each had
    exactly one eligible unused candidate left, so both were used rather
    than risk losing them to a concurrent session: TJSE/578949084 (an
    Acordao carrying three raw ASCII control characters -- U+001C/U+001D
    used as improvised quotes around a STF citation, U+0013 used as an
    opening parenthesis before a page reference -- the same defect shape
    as risk class 7 in ``knowledge/backlog/issue-1050.md``, resolved with
    a length-preserving substitution to ASCII `"`/`(`) and TJRS/458637070
    (a Sentenca with embedded raw HTML markup -- `<b>`/<table>`/`<tr>`/
    `<td>` -- resolved with the batch3 HTML-to-text cleaner). If corpus
    growth from a later concurrent batch changes the exact total, update
    the count here rather than treating a higher number as a failure --
    the two specific document hashes are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 123
    assert any(h.startswith("c002c5d5") for h in hashes), "TJSE batch13 document missing"
    assert any(h.startswith("eed26aff") for h in hashes), "TJRS batch13 document missing"


def test_real_store_reflects_batch14_corpus_growth() -> None:
    """Regression guard for #1050's fourteenth real DJEN sample batch.

    A genuinely independent, concurrent session (PR #1565) picked the same
    "batch13" label and landed the identical volume-tier strategy on the
    same starting snapshot (121 documents) -- it ingested TJSE/578949084
    and TJRS/458637070, the exact two documents this round also selected
    from the same eight-tribunal tied tier. Discovered via a merge conflict
    against ``origin/main`` after this round had already annotated and
    ingested five documents locally (TST/237077355, TJPI/22443810,
    TJRS/458637070, TJSE/578949084, TRF5/349055692, plus a sixth,
    TJSC/587254906, already reverted for an unrelated batch4 duplicate --
    see the risk class 11 note on ``test_real_store_reflects_batch13_corpus_growth``
    above).

    Reconciled as follows: TJRS/458637070 -- both sessions independently
    ran the raw source text through the identical batch3 HTML-to-text
    cleaner and produced byte-identical cleaned text, so ``document_id``
    (a hash of the cleaned text) matched exactly and the merge was a
    silent no-op for that document; this round's own second, redundant
    annotation of it was deleted (same ``annotator_config`` as the
    pre-existing one -- no independence value, same reasoning as the
    TJSC/batch4 case). TJSE/578949084 -- the two sessions chose *different*
    length-preserving substitutions for the same raw control character
    (this round: ASCII ``-``; PR #1565: ASCII ``(``), so the cleaned text
    differed and produced two genuinely different ``document_id``s for the
    same underlying real document -- keeping both would have been a true
    near-duplicate in the corpus (the same anti-pattern batch11 rejected
    for a near-identical TST pair), so this round's TJSE document and its
    annotation were deleted, keeping only PR #1565's already-merged
    version. The three documents PR #1565 did not touch --
    TST/237077355, TJPI/22443810, TRF5/349055692 -- are this batch's real,
    non-overlapping contribution: TST had raw ``<br>`` HTML markup in its
    source (cleaned with the batch3 helper), TJPI needed an
    ``ementa``-unmatched override (capa+ementa-estruturada export with no
    RELATORIO/VOTO to close against), TRF5 needed
    relatorio/custas/honorarios-unmatched overrides (all verified against
    the raw source text). New risk class 12 for
    ``knowledge/backlog/issue-1050.md``: two independent sessions can pick
    the *same* volume-tier candidate from a tied ``store_count`` scan and
    both ingest it before either merges -- unlike risk classes 8-10 (a
    session's own scan racing a concurrent *write*), this is two sessions'
    *read-time* candidate selection colliding, only surfacing as a merge
    conflict rather than a live dedup-check miss, because both sessions
    worked from disjoint local branches. If corpus growth from a later
    concurrent batch changes the exact total, update the count here rather
    than treating a higher number as a failure -- the three specific
    document hashes are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 126
    assert any(h.startswith("d6ee41ce") for h in hashes), "TJPI batch14 document missing"
    assert any(h.startswith("dfbd4832") for h in hashes), "TRF5 batch14 document missing"
    assert any(h.startswith("fe3392b2") for h in hashes), "TST batch14 document missing"


def test_real_store_reflects_batch15_corpus_growth() -> None:
    """Regression guard for #1050's fifteenth real DJEN sample batch.

    Snapshot before this batch: 126 documents (after batch14 merged,
    confirmed live via ``scripts/segmenter_governance_status.py``). This
    batch selected 6 never-used candidates from the lowest-``store_count``
    tribunals already represented in the corpus (TST, TJRJ x2, TJTO x2,
    TRF2), following the volume-over-diversity strategy documented for
    prior batches: TST/237077375 (prefix ``be29c768``), TJRJ/327497197
    (prefix ``bc5c53e9``), TJRJ/327515150 (prefix ``c6ea13e4``),
    TJTO/285693071 (prefix ``a808bd4b``), TJTO/285710292 (prefix
    ``f4321405``), TRF2/301247724 (prefix ``c7034ee0``).

    Four candidates (TST, TJTO x2, TRF2) had raw HTML markup embedded in
    ``texto_limpo`` (bare ``<br>``, ``<b>``/``<table>``/``</br>``, a full
    ``<html><head>...<body>`` wrapper) and needed the already-validated
    batch3 HTML-to-text cleaner (``docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py``)
    before annotation.

    Two candidates (TJTO/285693071, TRF2/301247724) hit the known
    same-length NBSP (U+00A0) -to-regular-space substitution defect first
    documented in batch4/batch13, but pervasively this time (12 and 33
    occurrences respectively across the whole document, not a single
    isolated instance) -- fixed programmatically by diffing the
    reconstructed (tags-stripped) text against the source character by
    character and reinserting the correct NBSP bytes into the tagged XML
    at the mapped positions, then re-verifying byte-identical
    reconstruction before ingesting. No subagent redo was needed.

    Four ``--allowed-unmatched-overrides`` entries were needed for
    dangling start/end pairs with no closing cue in the source text
    (``capitulo_merito`` x2, ``custas`` x2, ``honorarios`` x2,
    ``encerramento`` x1) -- each verified against the raw source text
    before declaring, the same established defect class as prior batches
    (a formulaic mention like "Sem custas nem honorários advocatícios"
    inline in the dispositivo, with no distinct closing phrase).

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the six specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 132
    assert any(h.startswith("be29c768") for h in hashes), "TST batch15 document missing"
    assert any(h.startswith("bc5c53e9") for h in hashes), "TJRJ/327497197 batch15 document missing"
    assert any(h.startswith("c6ea13e4") for h in hashes), "TJRJ/327515150 batch15 document missing"
    assert any(h.startswith("a808bd4b") for h in hashes), "TJTO/285693071 batch15 document missing"
    assert any(h.startswith("f4321405") for h in hashes), "TJTO/285710292 batch15 document missing"
    assert any(h.startswith("c7034ee0") for h in hashes), "TRF2 batch15 document missing"


def test_real_store_reflects_batch17_corpus_growth() -> None:
    """Regression guard for #1050's seventeenth real DJEN sample batch.

    Snapshot before this batch: 138 documents (after batch16 merged,
    confirmed live via ``scripts/segmenter_governance_status.py``). This
    batch selected 5 never-used candidates from the lowest-``store_count``
    tribunals already represented in the corpus (TJBA, TJMA x2, TJCE x2),
    following the volume-over-diversity strategy documented for prior
    batches: TJBA/574460085 (prefix ``391d30a3``), TJMA/42730832 (prefix
    ``853f47df``), TJMA/42736393 (prefix ``6f0cf54f``), TJCE/363647616
    (prefix ``40940035``), TJCE/363657243 (prefix ``ef286086``).

    A sixth originally-selected candidate, TJBA/574460088, was dropped
    before annotation: its raw source text scored
    ``difflib.SequenceMatcher.ratio()=0.98`` against TJBA/574460085 (same
    court, same judge, same embargos-de-declaracao template), a
    near-duplicate that would have violated #1050's own leakage-prevention
    acceptance criterion.

    TJBA/574460085 and both TJCE candidates had genuine NBSP (U+00A0)
    embedded in the source text stripped by the annotating subagent
    during "verbatim" transcription -- the same defect class first
    documented in batch13/15/16, fixed with the established diff-and-remap
    technique. Fixing it this time also caught and fixed a real bug in
    that technique's own script: a multi-character ``replace``/``delete``
    diff op mapped its end boundary to the *next* stripped character's raw
    position instead of the end of the *last* replaced character, which
    silently deleted any XML tag sitting exactly between the two (the
    existing "stripped text matches source" self-check cannot detect this,
    since removing a tag does not change the stripped text) -- caught only
    by adding a before/after XML-tag-multiset equality check.

    TJCE/363657243 also had a genuine annotation gap distinct from the
    already-documented "no closing cue at all" dangling-pair class: its
    ``relatorio`` pair had no ``_inicio`` at all, because the source has
    neither a heading nor the guideline's own "Trata-se de" fallback
    phrase -- fixed by tagging the report's first proper name as the de
    facto opening cue.

    Four ``--allowed-unmatched-overrides`` entries were needed for
    dangling start/end pairs with no closing cue in the source text
    (``relatorio`` in TJCE/363647616 -- the guideline's own documented
    "relatorio dispensado" waiver-clause pattern; ``capitulo_merito``,
    ``custas``, ``honorarios`` in TJMA/42730832) -- each verified against
    the raw source text before declaring.

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the five specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 143
    assert any(h.startswith("391d30a3") for h in hashes), "TJBA/574460085 batch17 document missing"
    assert any(h.startswith("853f47df") for h in hashes), "TJMA/42730832 batch17 document missing"
    assert any(h.startswith("6f0cf54f") for h in hashes), "TJMA/42736393 batch17 document missing"
    assert any(h.startswith("40940035") for h in hashes), "TJCE/363647616 batch17 document missing"
    assert any(h.startswith("ef286086") for h in hashes), "TJCE/363657243 batch17 document missing"


def test_real_store_reflects_batch19_corpus_growth() -> None:
    """Regression guard for #1050's nineteenth real DJEN sample batch.

    This batch is a *rescue*, not a fresh selection: the AgentRun-vs-Wisk
    concurrency in this lineage produced two competing PRs both claiming
    "batch 18" for #1050 (PR #1576 from this mechanism, PR #1577 from
    Wisk). Wisk merged first; PR #1576's six real, non-overlapping,
    already-verbatim-verified documents were rescued and reapplied on top
    of the post-batch18 ``main`` under the batch19 label instead of being
    discarded, since ``git merge-tree`` confirmed they are pure additions
    with no ``document_id`` overlap against what batch18 already merged.

    Six documents: TJMT/74430633 (prefix ``9aaf99ce``),
    TJRR/568209392 (prefix ``0c30c433``), TJRR/568328945 (prefix
    ``8ae9c060``), TRF3/42490599 (prefix ``4dc2c40b``), TRF5/349186353
    Sentenca (prefix ``d4435ee9``), TRF5/463264301 Acordao (prefix
    ``0fd41fbe``).

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the six specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 155
    assert any(h.startswith("9aaf99ce") for h in hashes), "TJMT/74430633 batch19 document missing"
    assert any(h.startswith("0c30c433") for h in hashes), "TJRR/568209392 batch19 document missing"
    assert any(h.startswith("8ae9c060") for h in hashes), "TJRR/568328945 batch19 document missing"
    assert any(h.startswith("4dc2c40b") for h in hashes), "TRF3/42490599 batch19 document missing"
    assert any(h.startswith("d4435ee9") for h in hashes), "TRF5/349186353 batch19 document missing"
    assert any(h.startswith("0fd41fbe") for h in hashes), "TRF5/463264301 batch19 document missing"


def test_real_store_reflects_batch23_corpus_growth() -> None:
    """Regression guard for #1050's twenty-third real DJEN sample batch.

    Six real TRF2 acordaos (9a Turma Especializada), all disjoint from the
    concurrent batch22 PR's tribunals (TJGO/TJPB/TJPA/TJRJ/TJTO) to avoid
    any document_id collision risk regardless of merge order: 301222629
    (prefix ``1d6350c1``), 301222677 (prefix ``33322a21``), 301222685
    (prefix ``aba71370``), 301222713 (prefix ``b8976111``), 301222792
    (prefix ``79891751``), 301228222 (prefix ``8744eb61``).

    This batch also found and fixed a real, previously-undocumented
    structural bug: nesting a single-anchor tag (``resultado``) directly
    inside a start/end pair's ``<inicio>``/``<fim>`` child is silently
    dropped by ``_text_element_to_labels`` (the ``_PAIR_ROLES`` branch in
    ``segmenter_dataset.store`` only emits the wrapper's own
    ``{base}_{role}`` label and never splices in that child's own nested
    items) -- round-trip text reconstruction still matches byte-for-byte,
    so naive verbatim-fidelity verification alone does not catch it. Two
    of three subagents in this batch (301222629, 301222792) had already
    tagged the operative ``resultado`` phrase but nested it inside
    ``<fim>...</fim>``; a third (301222713) did the same in its original
    output. All three were fixed by moving ``<resultado>`` to be a sibling
    of ``<inicio>``/``<fim>`` (still inside the pair's own wrapper
    element, or immediately after it closes) rather than a child of
    ``<fim>`` itself -- pure tag repositioning, no retyped content,
    reverified byte-for-byte after each fix. A fourth document
    (301222685) had a genuine risk-class-14 shape: its subagent declared
    ``acordao_decisorio`` unmatched (inicio-only) claiming "por
    unanimidade" appeared "mid-sentence rather than at the true close",
    but the raw source text has the identical boilerplate structure
    already used successfully as a closing cue by two sibling documents
    in this same batch -- fixed by adding the missing ``<fim>por
    unanimidade</fim>``, not by accepting an unverified override.

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the six specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 173
    assert any(h.startswith("1d6350c1") for h in hashes), "TRF2/301222629 batch23 document missing"
    assert any(h.startswith("33322a21") for h in hashes), "TRF2/301222677 batch23 document missing"
    assert any(h.startswith("aba71370") for h in hashes), "TRF2/301222685 batch23 document missing"
    assert any(h.startswith("b8976111") for h in hashes), "TRF2/301222713 batch23 document missing"
    assert any(h.startswith("79891751") for h in hashes), "TRF2/301222792 batch23 document missing"
    assert any(h.startswith("8744eb61") for h in hashes), "TRF2/301228222 batch23 document missing"


def test_real_store_reflects_batch26_corpus_growth() -> None:
    """Regression guard for #1050's twenty-sixth real DJEN sample batch.

    Snapshot before this batch: 191 documents (after batches 1-25 merged,
    including PR #1597's Codex-finding fixes and PR #1598's dedup.py
    performance fix, both landed 2026-09-24). A live scan of every
    ``data/segmenter_samples/*.jsonl`` candidate (Sentenca/Acordao only,
    2500-18000 chars, deduped against the store's already-ingested
    ``(tribunal, id)`` pairs) initially surfaced TJBA/574460088 and
    TJMA/42728925 as the only unused floor-compliant candidates among the
    lowest-``store_count`` tribunals -- both were rejected on a live
    ``difflib.SequenceMatcher.ratio()`` check against the whole store
    (0.980 against TJBA/574460085, already ingested; 0.968 against
    TJMA/42728353, already ingested), the same near-duplicate risk class
    batch17/batch25 already documented. Notably, ``knowledge/backlog/issue-1050.md``'s
    own batch24 narrative claims TJBA/574460088 was ingested that round,
    but a live grep of ``data/segmenter/documents`` for its source_uri
    found zero matches -- a real backlog/store inconsistency, flagged in
    this round's ``AgentDecision`` rather than silently trusted either
    way. TJCE/363694252 (13910 chars, Sentenca) was picked as the real
    replacement (max ratio 0.061 against the entire store). TJSC/587254831
    (raw 2336 chars, Acordao) was also selected, deliberately below the
    empirical ~2500-char selection floor: TJSC is the single most
    under-represented tribunal in the whole store (store_count=1) with
    zero remaining candidates at or above that floor, and #1050 explicitly
    asks for "multiple tribunals/sources" diversity, not just volume.
    TJSC/587254831's ``texto_limpo`` turned out to be raw, unwrapped HTML
    (``<html><head>...<body>`` with embedded ``<section>``/``<table>``
    markup) rather than plain text -- the same defect class documented
    since batch3/batch18/TRF4's exclusion, caught only because the first
    subagent's tagged output still carried the HTML wrapper verbatim. Fixed
    by running the batch3 HTML-to-text cleaner
    (``docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py``)
    on the raw text (2336 -> 1037 chars) before re-annotating; the cleaned
    text's near-duplicate check was reconfirmed clean (max ratio 0.118
    against the entire store).

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the two specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 193
    assert any(h.startswith("797cacef") for h in hashes), "TJCE/363694252 batch26 document missing"
    assert any(h.startswith("4f966854") for h in hashes), "TJSC/587254831 batch26 document missing"


def test_real_store_reflects_batch27_corpus_growth() -> None:
    """Regression guard for #1050's twenty-seventh real DJEN sample batch.

    Snapshot before this batch: 193 documents. A live scan of every
    ``data/segmenter_samples/*.jsonl`` candidate (Sentenca/Acordao only,
    >=2500 chars, deduped by ``(tribunal, id)`` against the store's
    already-ingested ``djen_sample_technique1`` source URIs) found the
    lowest non-exhausted, non-near-duplicate tribunal tier at
    ``store_count=6``: TJES, TJGO, TJPB, TJMT, TJPA, TJRJ, TJTO, TRF3, TRF5
    all tied. TRF6/TJMG/TJSC/TJRN/TJRS/TJSE/TJMS/TST were reconfirmed
    exhausted or near-duplicate-only (TJBA's single remaining candidate,
    574460088, and TJMA's, 42728925, are the same known near-duplicates
    batch26 already rejected at ratio 0.980/0.968 -- not reselected here).
    TRF4 was reconfirmed unusable per the already-documented risk class 16.

    TJES/577054715 (Sentenca, 3824 chars, JEC "projeto de sentenca" +
    homologacao format) and TJGO/543518267 (Sentenca, embargos de
    declaracao ruling, 4195 chars after ``html.unescape()`` -- the source
    ``texto_limpo`` carried raw HTML entities, the same recurring TJGO
    defect class already documented for batches 12/16/18/22) were picked:
    both tied at ``store_count=6`` before this batch, both real,
    never-used, and both confirmed clean of any near-duplicate by a live
    ``difflib.SequenceMatcher.ratio()`` check against the entire 193-document
    store (max ratio 0.114 and 0.054 respectively, far below any
    near-duplicate threshold used by prior batches).

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the two specific document hashes are the actual
    contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 195
    assert any(h.startswith("2e2ead10") for h in hashes), "TJES/577054715 batch27 document missing"
    assert any(h.startswith("fc6215c7") for h in hashes), "TJGO/543518267 batch27 document missing"


def test_real_store_reflects_batch28_corpus_growth() -> None:
    """Regression guard for #1050's twenty-eighth real DJEN sample batch.

    Snapshot before this batch: 195 documents (after batch27 merged, plus
    PR #1665's #1051 adjudication which only touches ``review_count``, not
    ``document_count``). ``scripts/segmenter_governance_status.py`` run
    live at the start of this round showed ``val_ceiling_at_full_adjudication``/
    ``test_ceiling_at_full_adjudication`` both at 29 -- one document short
    of RFC 0012 Sec 5 item 4's >=30/>=30 per-split floor even at 100%
    adjudication of the existing pool. Growing the corpus (not adjudicating
    it further) is the only lever that can raise that ceiling.

    A live scan of every ``data/segmenter_samples/*.jsonl`` candidate
    (Sentenca/Acordao only, >=2500 chars, deduped by ``(tribunal, id)``
    against the store's already-ingested ``djen_sample_technique1`` source
    URIs) found the lowest non-exhausted tribunal tier at ``store_count=6``:
    TJMA, TJPA, TJPB, TJRJ, TJTO, TRF3, TRF5, TJMT all tied (TJES/TJGO moved
    to 7 by batch27). TJMA was reconfirmed unusable -- its one remaining
    candidate (42728925) is the same near-duplicate batch26/batch27 already
    rejected (ratio 0.968 against an already-ingested TJMA document).

    TJPB/578828501 (Sentenca, Juizado Especial Civel de Campina Grande,
    cumprimento de sentenca, 4932 chars) and TJMT/74433596 (Sentenca, 6o
    Juizado Especial Civel de Cuiaba, 5230 chars) were picked: both real,
    never-used, both tied at ``store_count=6`` before this batch. Live
    ``difflib.SequenceMatcher.ratio()`` against the entire 195-document
    store: TJPB max ratio 0.025 (no similar document); TJMT max ratio 0.64
    against an already-ingested TJMT document from the same court
    (``djen_sample_technique1:batch1:TJMT:74430633``) -- inspected directly
    and confirmed to be template boilerplate similarity (same Juizado
    Especial Civel de Cuiaba "Vistos etc." opening formula), not a
    near-duplicate: different process numbers, different parties, different
    claims. Not rejected.

    If corpus growth from a later concurrent batch changes the exact
    total, update the count here rather than treating a higher number as
    a failure -- the two specific document hashes are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    hashes = {doc.source.source_hash for doc in documents}

    assert len(documents) >= 197
    assert any(h.startswith("9b4452b6") for h in hashes), "TJPB/578828501 batch28 document missing"
    assert any(h.startswith("a3716fe5") for h in hashes), "TJMT/74433596 batch28 document missing"


def test_main_prints_json_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store = SegmenterDatasetStore(tmp_path / "store")
    _write_document_and_annotation(store, "doc_" + "6" * 32, "ann_" + "6" * 32)

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    mod.main(["--store", str(tmp_path / "store")])  # type: ignore[attr-defined]

    out = capsys.readouterr().out
    first_line_block = out.split("\n\n", 1)[0]
    payload = json.loads(first_line_block)
    assert payload["document_count"] == 1
    assert "WARNING" in out


def test_real_store_reflects_1051_test_split_adjudication_round() -> None:
    """Regression guard for #1051's second and third real adjudicated reviews.

    Snapshot before this round: 197 documents, 32 accepted reviews
    (`val_count`=30, at the corpus-size ceiling reached by batch28;
    `test_count`=2, far behind). `scripts/segmenter_governance_status.py`
    run live at the start of this round confirmed the corpus-scale ceiling
    (#1050) no longer blocks the RFC 0012 Sec 5 item 4 floor
    (`val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication`
    both 30) -- the remaining gap is purely adjudication coverage on the
    TEST side (#1051).

    Two more documents were adjudicated this round via a genuinely
    independent second annotation (distinct `model_family`,
    `prompt_subagents:haiku` vs the first annotation's
    `prompt_subagents:general-purpose`) reconciled into an accepted
    ``ReviewRecord``: doc_0db5fffa04141a164fb9c48f11bb8c01 (TRF6 acordao,
    embargos de declaracao) and doc_174797b9bfde68303b3e00c43ac291fe (TRF2
    acordao, embargos de declaracao). Both were selected because a live
    simulation (``assign_splits`` with each candidate added to
    ``evaluation_eligible`` in isolation, before spending any annotation
    effort) showed they would each raise ``test_count`` -- confirming they
    move the metric that actually blocks the floor, not just
    ``review_count`` in general. ``assign_splits`` recomputes the whole
    val/test partition from a fixed hash order every time it runs, so which
    *specific* document lands in val vs test isn't controllable by
    identity -- only the aggregate counts are the real contract here.

    If corpus/review growth from a later concurrent round changes the
    exact totals, update the counts here rather than treating a higher
    number as a failure -- the two specific document hashes/ids are the
    actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    reviews = list(store.list_reviews())
    reviewed_document_ids = {r.document_id for r in reviews if r.status == "accepted"}

    assert len(reviews) >= 34
    assert "doc_0db5fffa04141a164fb9c48f11bb8c01" in reviewed_document_ids
    assert "doc_174797b9bfde68303b3e00c43ac291fe" in reviewed_document_ids

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["review_count"] >= 34
    assert status["test_count"] >= 4


def test_real_store_reflects_1051_kgxf50_round_adjudication() -> None:
    """Regression guard for #1051's 5th/6th/7th accepted reviews (round kgxf50).

    Snapshot before this round: 197 documents, 34 accepted reviews
    (`val_count`=30, at the corpus-size ceiling; `test_count`=4, still far
    behind the RFC 0012 Sec 5 item 4 floor of 30). Three more documents were
    adjudicated this round via a genuinely independent second annotation
    (`model_family=prompt_subagents:haiku`, distinct from the first
    annotation's `model_family=prompt_subagents:general-purpose`):
    `doc_d3de3dfe95769791db33077c54bd3724` (TJSC, acordao),
    `doc_4a8e16820fb9c8fa1d808d717d9a34d7` (TJMG, sentenca), and
    `doc_3b0be436ba6753185997c37b2b6b9765` (TJSE, acordao). All three were
    selected because a live simulation (`assign_splits` with each candidate
    added to `evaluation_eligible` in isolation, then jointly with the
    round's full batch, before spending any annotation effort) showed the
    joint addition raises `test_count` from 4 to 7 -- `assign_splits`
    recomputes the whole val/test partition from a fixed hash order every
    run, so which *specific* document lands in val vs test isn't
    identity-controllable, only the aggregate counts are the real contract.

    If corpus/review growth from a later concurrent round changes the exact
    totals, update the counts here rather than treating a higher number as a
    failure -- the three specific document ids are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    reviews = list(store.list_reviews())
    reviewed_document_ids = {r.document_id for r in reviews if r.status == "accepted"}

    assert len(reviews) >= 37
    assert "doc_d3de3dfe95769791db33077c54bd3724" in reviewed_document_ids
    assert "doc_4a8e16820fb9c8fa1d808d717d9a34d7" in reviewed_document_ids
    assert "doc_3b0be436ba6753185997c37b2b6b9765" in reviewed_document_ids

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["review_count"] >= 37
    assert status["test_count"] > 4


def test_real_store_reflects_1051_bomtmk_round_adjudication() -> None:
    """Regression guard for #1051's 8th/9th/10th accepted reviews (round bomtmk).

    Snapshot before this round: 197 documents, 37 accepted reviews
    (`val_count`=30, at the corpus-size ceiling; `test_count`=7, still far
    behind the RFC 0012 Sec 5 item 4 floor of 30). Three more documents were
    adjudicated this round via a genuinely independent second annotation
    (`model_family=prompt_subagents:haiku`, distinct from the first
    annotation's `model_family=prompt_subagents:general-purpose`):
    `doc_8904b2884e6177d2b61fd7462ce7539d` (TRF2, sentenca),
    `doc_6b29f96e41baeb5405c87bd09fb38d3d` (TJES, sentenca), and
    `doc_de65a409f2156cc18d43f96fa35347fc` (TJSE, acordao). All three were
    selected because a live simulation (`assign_splits` with each candidate
    added to `evaluation_eligible` in isolation, then jointly with the
    round's full batch, before spending any annotation effort) showed the
    joint addition raises `test_count` from 7 to 10 -- `assign_splits`
    recomputes the whole val/test partition from a fixed hash order every
    run, so which *specific* document lands in val vs test isn't
    identity-controllable, only the aggregate counts are the real contract.

    If corpus/review growth from a later concurrent round changes the exact
    totals, update the counts here rather than treating a higher number as a
    failure -- the three specific document ids are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    reviews = list(store.list_reviews())
    reviewed_document_ids = {r.document_id for r in reviews if r.status == "accepted"}

    assert len(reviews) >= 40
    assert "doc_8904b2884e6177d2b61fd7462ce7539d" in reviewed_document_ids
    assert "doc_6b29f96e41baeb5405c87bd09fb38d3d" in reviewed_document_ids
    assert "doc_de65a409f2156cc18d43f96fa35347fc" in reviewed_document_ids

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["review_count"] >= 40
    assert status["test_count"] > 7


def test_real_store_reflects_1051_uq3be8_round_adjudication() -> None:
    """Regression guard for #1051's 11th/12th/13th accepted reviews (round uq3be8).

    Snapshot before this round: 197 documents, 40 accepted reviews
    (`val_count`=30, at the corpus-size ceiling; `test_count`=10, still
    behind the RFC 0012 Sec 5 item 4 floor of 30). Three more documents were
    adjudicated via a genuinely independent second annotation
    (`model_family=prompt_subagents:haiku`, distinct from the first
    annotation's `model_family=prompt_subagents:general-purpose`):
    `doc_f6bf5be833edfed990b813302278409d` (TJRS, sentenca),
    `doc_cfa06dbce6009c921f4f66a5126c2056` (TJRS, sentenca), and
    `doc_9d8bb4320467e630a1d7805adac5c315` (TRF4, acordao). All three were
    selected because a live simulation (`assign_splits` with each candidate
    added to `evaluation_eligible` in isolation, then jointly with the
    round's full batch, before spending any annotation effort) showed the
    joint addition raises `test_count` from 10 to 13.

    If corpus/review growth from a later concurrent round changes the exact
    totals, update the counts here rather than treating a higher number as a
    failure -- the three specific document ids are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    reviews = list(store.list_reviews())
    reviewed_document_ids = {r.document_id for r in reviews if r.status == "accepted"}

    assert len(reviews) >= 43
    assert "doc_f6bf5be833edfed990b813302278409d" in reviewed_document_ids
    assert "doc_cfa06dbce6009c921f4f66a5126c2056" in reviewed_document_ids
    assert "doc_9d8bb4320467e630a1d7805adac5c315" in reviewed_document_ids

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["review_count"] >= 43
    assert status["test_count"] > 10


def test_real_store_reflects_1051_pg2bcv_round_adjudication() -> None:
    """Regression guard for #1051's 11th-15th accepted reviews (this round).

    Snapshot before this round: 197 documents, 40 accepted reviews
    (`val_count`=30, at the corpus-size ceiling; `test_count`=10, still
    behind the RFC 0012 Sec 5 item 4 floor of 30). Five more documents were
    adjudicated this round via a genuinely independent second annotation
    (`model_family=prompt_subagents:haiku`, distinct from the first
    annotation's `model_family=prompt_subagents:general-purpose`):
    `doc_1b3f5f7c10c405140aeae34dfb9eb25e` (TJES, sentenca),
    `doc_cef4677db81a15cd7104a72b26ac3131` (TJMT, sentenca),
    `doc_c8e8fed1aa63fab1538a9893a3b0b280` (TJRN, sentenca),
    `doc_cdd1225e01e312fee25cd7c3193f5766` (TJMT, sentenca), and
    `doc_a650dba8224a68a88a472ab9833e00d7` (TJMA, sentenca). All five were
    selected because a live simulation (`assign_splits` with each candidate
    added to `evaluation_eligible` jointly with the round's full batch,
    before spending any annotation effort) showed the joint addition raises
    `test_count` from 10 to 15 -- `assign_splits` recomputes the whole
    val/test partition from a fixed hash order every run, so which
    *specific* document lands in val vs test isn't identity-controllable,
    only the aggregate counts are the real contract.

    If corpus/review growth from a later concurrent round changes the exact
    totals, update the counts here rather than treating a higher number as a
    failure -- the five specific document ids are the actual contract.
    """
    store_dir = Path("data/segmenter")
    if not store_dir.exists():
        pytest.skip("data/segmenter not present in this checkout")

    store = SegmenterDatasetStore(store_dir)
    reviews = list(store.list_reviews())
    reviewed_document_ids = {r.document_id for r in reviews if r.status == "accepted"}

    assert len(reviews) >= 45
    assert "doc_1b3f5f7c10c405140aeae34dfb9eb25e" in reviewed_document_ids
    assert "doc_cef4677db81a15cd7104a72b26ac3131" in reviewed_document_ids
    assert "doc_c8e8fed1aa63fab1538a9893a3b0b280" in reviewed_document_ids
    assert "doc_cdd1225e01e312fee25cd7c3193f5766" in reviewed_document_ids
    assert "doc_a650dba8224a68a88a472ab9833e00d7" in reviewed_document_ids

    mod = load_script("segmenter_governance_status", "scripts/segmenter_governance_status.py")
    status = mod.compute_governance_status(store_dir)  # type: ignore[attr-defined]

    assert status["review_count"] >= 45
    assert status["test_count"] > 10
