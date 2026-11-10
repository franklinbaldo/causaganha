"""Testes para a Catraca Evolutiva do Torneio de Regexes (Tournament Ratchet)."""

from __future__ import annotations

import pytest

from causaganha.decisoes.regex_tournament import CompetitiveRegex, RegexTournament
from causaganha.decisoes.tournament_ratchet import (
    InvalidRegexPatternError,
    ThxParseError,
    TournamentRatchet,
)


def test_build_thx_prompt():
    prompt = TournamentRatchet.build_thx_prompt(
        decision_text="O autor requer a procedência...",
        expected_category="procedente",
        failed_on="improcedente",
        dispositivo_text="Pelo exposto, julgo procedente o pedido.",
    )
    assert "PROCEDENTE" in prompt
    assert "Pelo exposto, julgo procedente o pedido." in prompt
    assert "improcedente" in prompt
    assert "negative_pattern" in prompt


def test_parse_thx_candidate_valid():
    sample_json = """
    ```json
    {
      "pattern": "r\\"\\\\bjulgo\\\\s+procedente\\\\b\\"",
      "negative_pattern": "r\\"(?:parcialmente|em\\\\s+parte)\\"",
      "scope": "dispositivo",
      "explanation": "Padrão canônico de procedência com exclusão de parcial"
    }
    ```
    """
    candidate = TournamentRatchet.parse_thx_candidate(
        response_text=sample_json,
        category="procedente",
        pattern_id="synth_proc_1",
    )
    assert candidate.pattern_id == "synth_proc_1"
    assert candidate.category == "procedente"
    assert candidate.negative_pattern == r"(?:parcialmente|em\s+parte)"
    assert candidate.scope == "dispositivo"
    assert candidate.matches("julgo procedente o pedido")
    assert not candidate.matches("julgo procedente em parte")


def test_parse_thx_candidate_invalid_json():
    with pytest.raises(ThxParseError):
        TournamentRatchet.parse_thx_candidate(
            response_text="isso não é json...",
            category="procedente",
        )


def test_parse_thx_candidate_invalid_regex():
    bad_regex_json = '{"pattern": "[invalid(regex"}'
    with pytest.raises(InvalidRegexPatternError):
        TournamentRatchet.parse_thx_candidate(
            response_text=bad_regex_json,
            category="procedente",
        )


def test_ratchet_gate_promotes_clean_rule():
    tournament = RegexTournament(top_k=2)
    ratchet = TournamentRatchet(tournament=tournament, min_precision=0.90, max_allowed_fp=1)

    candidate = CompetitiveRegex(
        pattern_id="clean_proc",
        pattern=r"\bjulgo\s+procedente\b",
        category="procedente",
        negative_pattern=r"(?:parcialmente|em\s+parte)",
    )

    dataset = [
        {"texto": "julgo procedente o pedido", "desfecho_cpc": "procedente"},
        {"texto": "julgo procedente a ação", "desfecho_cpc": "procedente"},
        {"texto": "julgo improcedente", "desfecho_cpc": "improcedente"},
        {"texto": "julgo procedente em parte", "desfecho_cpc": "parcialmente procedente"},
    ]

    result = ratchet.gate_candidate(candidate, dataset)
    assert result.promoted is True
    assert result.status == "PROMOTED"
    assert result.precision == 1.0
    assert result.fp == 0
    assert "clean_proc" in [r.pattern_id for r in tournament.categories.get("procedente", [])]


def test_ratchet_gate_rejects_dirty_rule():
    tournament = RegexTournament(top_k=2)
    ratchet = TournamentRatchet(tournament=tournament, min_precision=0.90, max_allowed_fp=0)

    # Regra frouxa sem negative guard que confunde procedente com procedente em parte
    candidate = CompetitiveRegex(
        pattern_id="dirty_proc",
        pattern=r"\bprocedente\b",
        category="procedente",
    )

    dataset = [
        {"texto": "julgo procedente o pedido", "desfecho_cpc": "procedente"},
        {"texto": "julgo procedente em parte", "desfecho_cpc": "parcialmente procedente"},
        {"texto": "ação parcialmente procedente", "desfecho_cpc": "parcialmente procedente"},
    ]

    result = ratchet.gate_candidate(candidate, dataset)
    assert result.promoted is False
    assert result.status in {"DEMOTED", "CANDIDATE"}
    assert result.fp > 0


def test_synthesize_dispositivo_candidate():
    synth = TournamentRatchet.synthesize_dispositivo_candidate(
        dispositivo_snippet="Pelo exposto, julgo procedente a ação indenizatória.",
        category="procedente",
    )
    assert synth is not None
    assert synth.category == "procedente"
    assert synth.negative_pattern is not None
    assert synth.matches("julgo procedente")
    assert not synth.matches("julgo procedente em parte")
