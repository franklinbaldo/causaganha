"""Classificação Multi-Eixo de Documentos Judiciais e Publicações DJEN.

Coordena a classificação simultânea em dois eixos ortogonais:
- Eixo 1 (Espécie / Topologia Processual): Macro-categoria (Acórdão, Sentença, Interlocutória, Despacho)
  e Categoria Especializada (ex: ACORDAO_APELACAO, SENTENCA_CUMPRIMENTO_SENTENCA, DESPACHO_MERO_EXPEDIENTE).
- Eixo 2 (Resultado Dispositivo / Operativo): Desfecho prático (Procedente, Improcedente, Provido,
  Não Provido, Extinção da Execução, Tutela Deferida, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from causaganha.analysis.recurso_resolver import resolve_winner_polo
from causaganha.decisoes.regex_tournament import (
    ClassificationExplanation,
    RegexTournament,
    build_default_tournament,
)
from causaganha.decisoes.taxonomy import (
    DocumentTaxonomyRegistry,
    MacroCategory,
    TaxonomyClassification,
)


@dataclass
class MultiAxisClassification:
    """Resultado estruturado da classificação multi-eixo."""

    # Eixo 1: Espécie / Topologia Processual
    macro_categoria: str
    especie_ato: str

    # Eixo 2: Desfecho Operativo / Dispositivo
    desfecho_operativo: str
    confianca_desfecho: float
    winning_rule: str | None = None
    winning_section: str | None = None

    # Resolução de mérito / partes
    polo_vencedor: str = "unknown"
    tags: list[str] = field(default_factory=list)
    confidence_global: float = 0.0

    # Metadados adicionais
    explicacao: ClassificationExplanation | None = None
    taxonomia_raw: TaxonomyClassification | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_categoria": self.macro_categoria,
            "especie_ato": self.especie_ato,
            "desfecho_operativo": self.desfecho_operativo,
            "confianca_desfecho": round(self.confianca_desfecho, 4),
            "polo_vencedor": self.polo_vencedor,
            "winning_rule": self.winning_rule,
            "winning_section": self.winning_section,
            "confidence_global": round(self.confidence_global, 4),
            "tags": self.tags,
        }


class MultiAxisJudicialClassifier:
    """Classificador unificado de múltiplos eixos processuais."""

    def __init__(
        self,
        tournament: RegexTournament | None = None,
        taxonomy: DocumentTaxonomyRegistry | None = None,
    ):
        self.tournament = tournament or build_default_tournament()
        self.taxonomy = taxonomy or DocumentTaxonomyRegistry()

    def classify(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        sections: dict[str, str] | None = None,
        section_weights: dict[str, float] | None = None,
    ) -> MultiAxisClassification:
        meta = metadata or {}

        # 1. Classificação no Eixo 1 (Espécie / Topologia)
        tax_res = self.taxonomy.classify(text, metadata=meta)

        # 2. Classificação no Eixo 2 (Desfecho Operativo)
        eval_sections = sections
        if not eval_sections and "dispositivo" in meta and meta["dispositivo"]:
            eval_sections = {"dispositivo": str(meta["dispositivo"]), "full": text}

        explanation = self.tournament.classify_with_explanation(
            text, sections=eval_sections, section_weights=section_weights
        )

        outcome = explanation.category
        conf_desfecho = explanation.confidence
        winning_rule_id = explanation.winning_rule.pattern_id if explanation.winning_rule else None

        # Se for um despacho de mero expediente e o torneio não encontrou desfecho terminativo
        if tax_res.macro_category == MacroCategory.DESPACHO and outcome == "unknown":
            outcome = "despacho de expediente"
            conf_desfecho = 0.95

        # 3. Resolução de Polo Vencedor Invariante
        recorrente_polo = None
        lower_text = text.lower()
        if (
            "apelação da ré" in lower_text
            or "recurso do réu" in lower_text
            or "recorrente: ré" in lower_text
        ):
            recorrente_polo = "P"
        elif (
            "apelação do autor" in lower_text
            or "recurso da autora" in lower_text
            or "recorrente: autor" in lower_text
        ):
            recorrente_polo = "A"

        polo = resolve_winner_polo(outcome, recorrente_polo)
        if outcome in {"tutela deferida"}:
            polo = "A"
        elif outcome in {"tutela indeferida"}:
            polo = "P"
        elif outcome in {"extinção da execução"}:
            polo = "draw"

        # Combinação de tags
        combined_tags = list(tax_res.tags)
        if outcome != "unknown":
            combined_tags.append(f"desfecho:{outcome.replace(' ', '_')}")

        conf_global = round((tax_res.confidence * 0.4) + (conf_desfecho * 0.6), 4)

        return MultiAxisClassification(
            macro_categoria=tax_res.macro_category.value,
            especie_ato=tax_res.specific_category,
            desfecho_operativo=outcome,
            confianca_desfecho=conf_desfecho,
            winning_rule=winning_rule_id,
            winning_section=explanation.winning_section,
            polo_vencedor=polo,
            tags=combined_tags,
            confidence_global=conf_global,
            explicacao=explanation,
            taxonomia_raw=tax_res,
        )
