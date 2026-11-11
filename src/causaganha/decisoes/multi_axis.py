"""Classificação Multi-Eixo de Documentos Judiciais e Publicações DJEN.

Coordena a classificação simultânea em três eixos ortogonais:
- Eixo 1 (Espécie / Topologia Processual): Macro-categoria (Acórdão, Sentença, Interlocutória, Despacho)
  e Categoria Especializada (ex: ACORDAO_APELACAO, SENTENCA_CUMPRIMENTO_SENTENCA, DESPACHO_MERO_EXPEDIENTE).
- Eixo 1.5 (Classe Processual TPU CNJ + Enriquecimento DataJud): Código e nome oficial da classe
  na Tabela Processual Unificada do CNJ (`[7] Procedimento Comum Cível`, `[198] Apelação Cível`, etc.),
  obtidos do `acervo.sqlite` (DataJud) ou extraídos do cabeçalho/taxonomia.
- Eixo 2 (Resultado Dispositivo / Operativo): Desfecho prático (Procedente, Improcedente, Provido,
  Não Provido, Extinção da Execução, Tutela Deferida, etc.), combinando `RegexTournament` (Master Regex),
  Oráculo TPU DataJud e Fallback ML (`WeakSupervisionOutcomeFallback`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from causaganha.analysis.recurso_resolver import resolve_winner_polo
from causaganha.decisoes.classe_processual import (
    ClasseProcessualExtractor,
    ClasseProcessualResult,
)
from causaganha.decisoes.ml_fallback import WeakSupervisionOutcomeFallback
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

_RE_RECORRENTE_AUTOR = re.compile(
    r"\b(?:"
    r"(?:apela[cç][aã]o|recurso(?:\s+inominado|\s+especial|\s+extraordin[aá]rio)?|agravo|apelo|embargos)"
    r"\s+(?:interpost[oa]\s+pel[oa]\s+|d[oa]\s+|manejad[oa]\s+pel[oa]\s+)?(?:parte\s+)?(?:autor[a]?|requerente|exequente|impetrante)"
    r"|inconformad[oa]\s*,\s*(?:a\s+parte\s+)?(?:autor[a]?|requerente)\s+interp[oô]s"
    r"|(?:recorrente|apelante|agravante)\s*:\s*(?:parte\s+)?(?:autor[a]?|requerente|minist[eé]rio\s+p[uú]blico)"
    r")\b",
    re.IGNORECASE,
)

_RE_RECORRENTE_REU = re.compile(
    r"\b(?:"
    r"(?:apela[cç][aã]o|recurso(?:\s+inominado|\s+especial|\s+extraordin[aá]rio)?|agravo|apelo|embargos)"
    r"\s+(?:interpost[oa]\s+pel[oa]\s+|d[oa]\s+|manejad[oa]\s+pel[oa]\s+)?(?:parte\s+)?(?:r[eé]u?|requerid[oa]|executad[oa]|banco|seguradora|inss|estado|munic[ií]pio|autarquia|defesa|acusad[oa])"
    r"|inconformad[oa]\s*,\s*(?:a\s+parte\s+|o\s+)?(?:r[eé]u?|requerid[oa]|banco|inss|defesa)\s+interp[oô]s"
    r"|(?:recorrente|apelante|agravante)\s*:\s*(?:parte\s+)?(?:r[eé]u?|requerid[oa])"
    r"|mantendo(?:-se)?\s+(?:os\s+demais\s+termos\s+da\s+)?a?\s*senten[cç]a\s+condenat[oó]ria"
    r")\b",
    re.IGNORECASE,
)

_RE_HEADER_APPELLANT = re.compile(
    r"(?:APELANTE|AGRAVANTE|RECORRENTE|EMBARGANTE)\s*[-:]\s*([^\n\r]{3,90})",
    re.IGNORECASE,
)
_RE_HEADER_APPELLEE = re.compile(
    r"(?:APELAD[OA]|AGRAVAD[OA]|RECORRID[OA]|EMBARGAD[OA])\s*[-:]\s*([^\n\r]{3,90})",
    re.IGNORECASE,
)
_RE_INSTITUTIONAL_DEFENDANT = re.compile(
    r"\b(?:BANCO|FINANCIAMENTO|CREDITO|CART[AÃ]O|SEGURADORA|SEGURADOR|ENERGISA|EQUATORIAL|"
    r"TELEFONICA|CLARO|TIM\s|VIVO|OI\s|SABESP|COPASA|COMPANHIA|INSS|INSTITUTO\s+NACIONAL|"
    r"ESTADO\s+D[OEA]|MUNIC[IÍ]PIO\s+D[OEA]|UNI[AÃ]O\s+FEDERAL|FAZENDA\s+P[UÚ]BLICA|"
    r"DETRAN|DER\b|CAIXA\s+ECON[OÔ]MICA|BRADESCO|ITA[UÚ]|SANTANDER|PAN\s+S|BMG|C6\s|NUBANK|MERCADO\s+PAGO|MERCADO\s+CREDITO)\b",
    re.IGNORECASE,
)


def _infer_recorrente_polo(
    text: str, meta: dict[str, Any], classe_codigo: int | None = None
) -> str | None:
    """Infere se o recorrente é o Polo Ativo ('A') ou Passivo ('P') no recurso."""
    explicit = meta.get("recorrente_polo")
    if explicit in {"A", "P"}:
        return str(explicit)

    if _RE_RECORRENTE_REU.search(text):
        return "P"
    if _RE_RECORRENTE_AUTOR.search(text):
        return "A"

    header = text[:1600]
    m_app = _RE_HEADER_APPELLANT.search(header)
    m_ape = _RE_HEADER_APPELLEE.search(header)
    app_name = m_app.group(1).strip() if m_app else ""
    ape_name = m_ape.group(1).strip() if m_ape else ""

    # Se for Apelação Criminal e o apelado é o Ministério Público -> réu apelou ('P')
    if ape_name and "MINIST" in ape_name.upper() and "PUBLICO" in ape_name.upper():
        return "P"
    if app_name and "MINIST" in app_name.upper() and "PUBLICO" in app_name.upper():
        return "A"

    # Em demandas cíveis/consumidor/previdenciárias (exceto Execução Fiscal 1116 e Busca e Apreensão 81):
    if classe_codigo not in {81, 1116, 159}:
        app_is_inst = bool(_RE_INSTITUTIONAL_DEFENDANT.search(app_name))
        ape_is_inst = bool(_RE_INSTITUTIONAL_DEFENDANT.search(ape_name))
        if app_is_inst and not ape_is_inst:
            return "P"
        if ape_is_inst and not app_is_inst:
            return "A"

    return None


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

    # Eixo 1.5: Classe Processual TPU CNJ & Enriquecimento DataJud
    classe_codigo: int | None = None
    classe_nome: str = "Procedimento Comum Cível"
    origem_classe: str = "inferencia_taxonomia"
    assunto_principal: str | None = None
    datajud_desfecho_tpu: str | None = None

    # Resolução de mérito / partes
    polo_vencedor: str = "unknown"
    tags: list[str] = field(default_factory=list)
    confidence_global: float = 0.0

    # Metadados adicionais
    explicacao: ClassificationExplanation | None = None
    taxonomia_raw: TaxonomyClassification | None = None
    classe_raw: ClasseProcessualResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_categoria": self.macro_categoria,
            "especie_ato": self.especie_ato,
            "classe_codigo": self.classe_codigo,
            "classe_nome": self.classe_nome,
            "origem_classe": self.origem_classe,
            "assunto_principal": self.assunto_principal,
            "datajud_desfecho_tpu": self.datajud_desfecho_tpu,
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
        classe_extractor: ClasseProcessualExtractor | None = None,
        ml_fallback: WeakSupervisionOutcomeFallback | None = None,
        enable_ml_fallback: bool = True,
    ):
        self.tournament = tournament or build_default_tournament()
        self.taxonomy = taxonomy or DocumentTaxonomyRegistry()
        self.classe_extractor = classe_extractor or ClasseProcessualExtractor()
        self.enable_ml_fallback = enable_ml_fallback
        self.ml_fallback = ml_fallback or (
            WeakSupervisionOutcomeFallback() if enable_ml_fallback else None
        )

    def fit_fallback_from_corpus(
        self,
        texts: list[str],
        labels: list[str],
        confidences: list[float] | None = None,
        min_confidence: float = 0.85,
    ) -> int:
        """Treina o modelo TF-IDF + Random Forest com decisões de alta confiança do lote."""
        if self.ml_fallback is None:
            self.ml_fallback = WeakSupervisionOutcomeFallback()
        return self.ml_fallback.fit_from_corpus(
            texts=texts,
            labels=labels,
            confidences=confidences,
            min_confidence=min_confidence,
        )

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

        # 1.5 Extração e Enriquecimento da Classe Processual (DataJud `acervo.sqlite` + NER Cabeçalho)
        classe_res = self.classe_extractor.extract(
            text=text,
            metadata=meta,
            especie_ato=tax_res.specific_category,
            macro_categoria=tax_res.macro_category.value,
        )

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
        winning_sec = explanation.winning_section

        # Cascata determinística e estatística caso o RegexTournament retorne "unknown"
        if outcome == "unknown":
            if tax_res.macro_category in {
                MacroCategory.DESPACHO,
                MacroCategory.PUBLICACAO_COMUNICACAO,
                MacroCategory.ATO_CARTORARIO,
                MacroCategory.EDITAL,
            }:
                outcome = "despacho de expediente"
                conf_desfecho = 0.94
                winning_rule_id = "taxonomy_despacho_expediente"
                winning_sec = "cabecalho"
            elif tax_res.specific_category == "SENTENCA_HOMOLOGATORIA_LEIGA":
                outcome = "homologação de decisão leiga"
                conf_desfecho = 0.94
                winning_rule_id = "taxonomy_homologatoria_leiga"
                winning_sec = "dispositivo"
            elif tax_res.specific_category == "SENTENCA_HOMOLOGATORIA_ACORDO":
                outcome = "acordo"
                conf_desfecho = 0.94
                winning_rule_id = "taxonomy_homologatoria_acordo"
                winning_sec = "dispositivo"
            elif tax_res.specific_category == "SENTENCA_EXTINTIVA_SEM_MERITO":
                outcome = "extinto sem mérito"
                conf_desfecho = 0.93
                winning_rule_id = "taxonomy_extintiva_sem_merito"
                winning_sec = "dispositivo"
            elif classe_res.datajud_desfecho_tpu:
                outcome = classe_res.datajud_desfecho_tpu
                conf_desfecho = 0.91
                winning_rule_id = f"datajud_tpu_{classe_res.datajud_movimento_codigo}"
                winning_sec = "datajud_oracle"
            elif self.enable_ml_fallback and self.ml_fallback is not None:
                fb = self.ml_fallback.predict(
                    text,
                    sections=eval_sections,
                    macro_categoria=tax_res.macro_category.value,
                )
                if fb.category != "unknown":
                    outcome = fb.category
                    conf_desfecho = fb.confidence
                    winning_rule_id = fb.rule_id
                    winning_sec = "ml_fallback"

        # 3. Resolução de Polo Vencedor Invariante
        recorrente_polo = _infer_recorrente_polo(text, meta, classe_res.classe_codigo)
        polo = resolve_winner_polo(outcome, recorrente_polo)
        if outcome == "tutela deferida":
            polo = "A"
        elif outcome in {"tutela indeferida", "extinto sem mérito"} and polo == "unknown":
            polo = "P"
        elif outcome in {"extinção da execução", "homologação de decisão leiga"}:
            polo = "draw"
        elif outcome == "não conhecido" and recorrente_polo in {"A", "P"}:
            polo = "P" if recorrente_polo == "A" else "A"

        # Combinação de tags
        combined_tags = list(tax_res.tags)
        if classe_res.classe_codigo is not None:
            combined_tags.append(f"tpu_classe:{classe_res.classe_codigo}")
        if classe_res.origem_classe == "datajud_acervo":
            combined_tags.append("enriquecido_datajud")
        if outcome != "unknown":
            combined_tags.append(f"desfecho:{outcome.replace(' ', '_')}")

        conf_global = round(
            (tax_res.confidence * 0.3)
            + (classe_res.confianca_classe * 0.2)
            + (conf_desfecho * 0.5),
            4,
        )

        return MultiAxisClassification(
            macro_categoria=tax_res.macro_category.value,
            especie_ato=tax_res.specific_category,
            classe_codigo=classe_res.classe_codigo,
            classe_nome=classe_res.classe_nome,
            origem_classe=classe_res.origem_classe,
            assunto_principal=classe_res.assunto_principal,
            datajud_desfecho_tpu=classe_res.datajud_desfecho_tpu,
            desfecho_operativo=outcome,
            confianca_desfecho=conf_desfecho,
            winning_rule=winning_rule_id,
            winning_section=winning_sec,
            polo_vencedor=polo,
            tags=combined_tags,
            confidence_global=conf_global,
            explicacao=explanation,
            taxonomia_raw=tax_res,
            classe_raw=classe_res,
        )
