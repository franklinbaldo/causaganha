"""Testes para a Esteira em 3 Estágios de Open NER (Descoberta -> Síntese -> Julgamento)."""

from __future__ import annotations

import pytest

from causaganha.decisoes.open_ner_tournament import (
    DiscoveredEntity,
    OpenNerListExpectedError,
    OpenNerParseError,
    OpenNerTournamentManager,
)
from causaganha.decisoes.regex_tournament import CompetitiveRegex


def test_discovery_prompt_generation():
    passage = "Fixo o prazo de 15 dias para cumprimento sob pena de multa diária de R$ 500,00."
    prompt = OpenNerTournamentManager.build_discovery_prompt(passage)
    assert "ABERTA" in prompt
    assert passage in prompt
    assert "entity_type" in prompt


def test_parse_discovery_response():
    sample_json = """
    [
      {
        "entity_type": "PRAZO_CUMPRIMENTO",
        "literal": "no prazo de 15 (quinze) dias",
        "attributes": { "dias": 15 }
      },
      {
        "entity_type": "ASTREINTES_TETO",
        "literal": "limitada ao montante de R$ 10.000,00",
        "attributes": { "teto": 10000.00 }
      }
    ]
    """
    entities = OpenNerTournamentManager.parse_discovery_response(sample_json)
    assert len(entities) == 2
    assert entities[0].entity_type == "PRAZO_CUMPRIMENTO"
    assert entities[0].literal == "no prazo de 15 (quinze) dias"
    assert entities[1].entity_type == "ASTREINTES_TETO"


def test_parse_discovery_invalid_response():
    with pytest.raises(OpenNerListExpectedError):
        OpenNerTournamentManager.parse_discovery_response('{"nao_e": "lista"}')

    with pytest.raises(OpenNerParseError):
        OpenNerTournamentManager.parse_discovery_response("texto puro sem json")


def test_synthesis_prompt_generation():
    ent = DiscoveredEntity(
        entity_type="ASTREINTES_TETO",
        literal="limitada ao teto de R$ 5.000,00",
        context_snippet="multa diária de R$ 200,00 limitada ao teto de R$ 5.000,00",
    )
    prompt = OpenNerTournamentManager.build_synthesis_prompt(ent)
    assert "ASTREINTES_TETO" in prompt
    assert "limitada ao teto de R$ 5.000,00" in prompt
    assert "negative_pattern" in prompt


def test_parse_synthesis_response_and_compilation():
    sample_json = """
    ```json
    {
      "pattern": "r\\"\\\\blimitad[ao]\\\\s+(?:ao\\\\s+teto\\\\s+de\\\\s+)?R\\\\$\\\\s*([\\\\d.,]+)\\\\b\\"",
      "negative_pattern": "r\\"(?:não\\\\s+limitada|sem\\\\s+limite)\\"",
      "capture_group": 1,
      "explanation": "Captura limite máximo de multa com trava de negação"
    }
    ```
    """
    candidate = OpenNerTournamentManager.parse_synthesis_response(
        sample_json, entity_type="ASTREINTES_TETO", pattern_id="teto_multa_v1"
    )
    assert candidate.pattern_id == "teto_multa_v1"
    assert candidate.category == "astreintes_teto"
    assert candidate.matches("multa diária limitada ao teto de R$ 5.000,00")
    # Trava negativa impede falso positivo
    assert not candidate.matches("multa sem limite de valor")


def test_adjudicator_clean_vs_dirty_extraction():
    # Regex precisa e cirúrgica
    good_rule = CompetitiveRegex(
        pattern_id="clean_rule",
        pattern=r"\bno\s+prazo\s+de\s+\d+\s+dias\b",
        category="prazo",
    )
    verdict = OpenNerTournamentManager.adjudicate_candidate_extraction(
        candidate_rule=good_rule,
        sample_text="Intime-se para cumprimento no prazo de 15 dias sob pena de revelia.",
        expected_target="no prazo de 15 dias",
    )
    assert verdict.is_valid is True
    assert verdict.is_clean_capture is True
    assert verdict.quality_score >= 0.9

    # Regex frouxa que captura texto irrelevante
    bad_rule = CompetitiveRegex(
        pattern_id="bad_rule",
        pattern=r"\bIntime-se.+sob\s+pena\b",
        category="prazo",
    )
    verdict_bad = OpenNerTournamentManager.adjudicate_candidate_extraction(
        candidate_rule=bad_rule,
        sample_text="Intime-se para cumprimento no prazo de 15 dias sob pena de revelia.",
        expected_target="no prazo de 15 dias",
    )
    assert verdict_bad.is_clean_capture is False  # Captura excessiva/ruidosa


def test_judge_promotes_only_best_regexes():
    manager = OpenNerTournamentManager(top_k=2, min_precision=0.90)

    # 1. Candidata Excelente (alta precisão)
    clean_candidate = CompetitiveRegex(
        pattern_id="reg_clean",
        pattern=r"\blimitad[ao]\s+a\s+R\$\s*[\d.,]+\b",
        category="astreintes_teto",
    )

    # 2. Candidata Frouxa (que dá falso positivo em outras coisas)
    loose_candidate = CompetitiveRegex(
        pattern_id="reg_loose",
        pattern=r"\bR\$\s*[\d.,]+\b",
        category="astreintes_teto",
    )

    validation_dataset = [
        {
            "texto": "Multa diária limitada a R$ 10.000,00",
            "target_literal": "limitada a R$ 10.000,00",
        },
        {
            "texto": "Fixada multa com valor limitado a R$ 5.000,00",
            "target_literal": "limitado a R$ 5.000,00",
        },
        # Documento sem teto (apenas valor de condenação normal)
        {"texto": "Condeno o réu ao pagamento de R$ 20.000,00", "target_literal": None},
    ]

    # Julgamento da candidata excelente
    res_clean = manager.judge_and_promote(clean_candidate, validation_dataset)
    assert res_clean["promoted"] is True
    assert res_clean["precision"] == 1.0
    assert res_clean["fp"] == 0

    # Julgamento da candidata frouxa
    res_loose = manager.judge_and_promote(loose_candidate, validation_dataset)
    assert res_loose["promoted"] is False
    assert res_loose["fp"] >= 1

    # Confirma que no catálogo oficial SÓ a melhor regex sobreviveu
    best = manager.get_best_regexes("astreintes_teto")
    assert len(best) == 1
    assert best[0].pattern_id == "reg_clean"
