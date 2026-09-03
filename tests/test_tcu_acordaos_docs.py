"""Doc-consistency contract for docs/data/tcu-acordaos.md.

#1028 closed #1012 with a real live investigation: 1992-2016 is declared
ineligible for canonical identity (no candidate field is collision-free
across every fully-tested year). #984 (the original bulk-proof issue) is
also closed. The doc must reflect both outcomes instead of describing them
as still-open decisions — see #1029.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/data/tcu-acordaos.md"


def _doc_text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_does_not_claim_984_or_1012_are_still_open() -> None:
    doc = _doc_text()

    assert "#984 permanece aberta" not in doc
    assert "não deve ser assumido como resolvido" not in doc


def test_declares_1992_2016_ineligible_with_rationale_and_evidence_reference() -> None:
    doc = _doc_text()

    assert "inelegí" in doc.lower()
    assert "#1028" in doc
    assert "tcu-acordaos-identity-1992-2016.json" in doc


def test_treats_all_25_pre_2017_years_from_real_investigation_not_neighbor_inference() -> None:
    doc = _doc_text()

    assert "25 anos" in doc
    assert "vizinh" not in doc.lower()


def test_distinguishes_identity_eligibility_from_actual_publication() -> None:
    doc = _doc_text()

    assert "elegí" in doc.lower()
    assert "#1022" in doc
    assert "publicad" in doc.lower()


def test_does_not_announce_2017_2026_as_publicly_available_before_1022() -> None:
    doc = _doc_text()

    assert "2017–2026 disponível" not in doc
    assert "2017-2026 disponível" not in doc


def test_references_the_causal_chain_of_issues() -> None:
    doc = _doc_text()

    for ref in ("#1011", "#1022", "#1028"):
        assert ref in doc
