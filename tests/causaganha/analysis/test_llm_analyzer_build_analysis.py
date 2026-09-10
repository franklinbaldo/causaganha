"""_build_analysis must preserve every rich field the LLM prompt asks for."""

from __future__ import annotations

from causaganha.analysis.llm_analyzer import _build_analysis


def test_build_analysis_preserves_precedents() -> None:
    parsed = {
        "outcome": "procedente",
        "decision_type": "sentença",
        "precedents": {"Tema 971 STJ": "confirmado"},
    }

    analysis = _build_analysis(parsed, intimation_id=1)

    assert analysis.precedents == {"Tema 971 STJ": "confirmado"}


def test_build_analysis_defaults_precedents_to_empty_dict_when_absent() -> None:
    parsed = {"outcome": "procedente", "decision_type": "sentença"}

    analysis = _build_analysis(parsed, intimation_id=1)

    assert analysis.precedents == {}
