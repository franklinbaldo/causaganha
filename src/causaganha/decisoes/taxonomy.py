"""Taxonomia Aberta e Especializada de Documentos Judiciais e Publicações DJEN.

Permite classificar e especializar hierarquicamente publicações jurídicas:
- Nível 1 (Macro-Topologia): ACORDAO, SENTENCA, DECISAO_INTERLOCUTORIA, DECISAO_MONOCRATICA,
                             DESPACHO, PUBLICACAO_COMUNICACAO, EDITAL, ATO_CARTORARIO.
- Nível 2 (Espécie Especializada): Ex.: EDITAL_CITACAO, INTIMACAO_AUDIENCIA, ACORDAO_APELACAO,
                                   DECISAO_TUTELA_URGENCIA, SENTENCA_HOMOLOGATORIA, etc.
- Nível 3 (Tags / Facetas): ["urgencia", "prazo_fatal", "reu_incerto", "conciliacao"].

Arquitetura Aberta e Extensível:
O DocumentTaxonomyRegistry aceita o registro dinâmico de novas categorias e regras
conforme novas classes processuais, tribunais ou parquets forem incorporados pela Flywheel.
"""

from __future__ import annotations

import enum
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable


class MacroCategory(str, enum.Enum):
    """Categorias macro-estruturais do ordenamento processual."""

    ACORDAO = "ACORDAO"
    SENTENCA = "SENTENCA"
    DECISAO_INTERLOCUTORIA = "DECISAO_INTERLOCUTORIA"
    DECISAO_MONOCRATICA = "DECISAO_MONOCRATICA"
    DESPACHO = "DESPACHO"
    PUBLICACAO_COMUNICACAO = "PUBLICACAO_COMUNICACAO"
    EDITAL = "EDITAL"
    ATO_CARTORARIO = "ATO_CARTORARIO"
    OUTRO = "OUTRO"


@dataclass
class TaxonomyClassification:
    """Resultado hierárquico da classificação taxonômica especializada."""

    macro_category: MacroCategory
    specific_category: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    rule_matched: str = "default_fallback"
    cnj_class_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "macro_category": self.macro_category.value,
            "specific_category": self.specific_category,
            "tags": self.tags,
            "confidence": round(self.confidence, 4),
            "rule_matched": self.rule_matched,
            "cnj_class_hint": self.cnj_class_hint,
        }


def _normalize(s: Any) -> str:
    if not isinstance(s, str):
        return ""
    norm = unicodedata.normalize("NFKD", s)
    return "".join(c for c in norm if not unicodedata.combining(c)).lower().strip()


@dataclass
class TaxonomyRule:
    name: str
    priority: int  # Maior prioridade roda primeiro
    matcher: Callable[[str, dict[str, Any]], bool]
    classifier: Callable[[str, dict[str, Any]], TaxonomyClassification]


class DocumentTaxonomyRegistry:
    """Registro aberto e extensível de taxonomia para documentos jurídicos."""

    def __init__(self):
        self._rules: list[TaxonomyRule] = []
        self._register_default_rules()

    def register_rule(
        self,
        name: str,
        priority: int,
        matcher: Callable[[str, dict[str, Any]], bool],
        classifier: Callable[[str, dict[str, Any]], TaxonomyClassification],
    ) -> None:
        """Permite que novos tribunais, usuários ou a flywheel registrem regras dinâmicas."""
        rule = TaxonomyRule(
            name=name,
            priority=priority,
            matcher=matcher,
            classifier=classifier,
        )
        self._rules.append(rule)
        # Ordena por prioridade decrescente
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def classify(self, text: str, metadata: dict[str, Any] | None = None) -> TaxonomyClassification:
        meta = metadata or {}
        text_norm = _normalize(text[:3000])  # Prefixo significativo para cabeçalho e abertura

        for rule in self._rules:
            try:
                if rule.matcher(text_norm, meta):
                    res = rule.classifier(text_norm, meta)
                    res.rule_matched = rule.name
                    return res
            except (ValueError, KeyError, TypeError, AttributeError, IndexError):
                continue

        return TaxonomyClassification(
            macro_category=MacroCategory.OUTRO,
            specific_category="DOCUMENTO_GENERICO",
            tags=[],
            confidence=0.5,
            rule_matched="fallback_default",
        )

    def _register_default_rules(self) -> None:
        """Registra a taxonomia canônica inicial com resolução estrita de conflitos.

        Princípio de Precedência:
        1. Metadado explícito de doc_type do DJEN tem prioridade absoluta sobre menções lexicais.
        2. Cabeçalho formal (primeiros 350 caracteres) tem prioridade sobre corpo/narrativa.
        3. Menções incidentais no corpo (ex: 'citado por edital' no relatório de uma sentença)
           são adicionadas como tags, mas NÃO alteram a macro-categoria do ato decisório.
        """

        # -------------------------------------------------------------
        # 1. DECISÃO MONOCRÁTICA (Prioridade 105)
        # -------------------------------------------------------------
        def match_monocratica(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if "monocratica" in doc_type:
                return True
            header = text[:350]
            return bool("decisao monocratica" in header)

        def classify_monocratica(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            tags = ["segundo_grau", "decisao_unipessoal"]
            if meta.get("relator"):
                tags.append("relator_identificado")
            if "art. 932" in text or "nao conheco" in text or "nego seguimento" in text:
                tags.append("art_932_cpc")
            return TaxonomyClassification(
                macro_category=MacroCategory.DECISAO_MONOCRATICA,
                specific_category="DECISAO_MONOCRATICA_RELATOR",
                tags=tags,
                confidence=0.97,
            )

        self.register_rule("monocratica_specialized", 105, match_monocratica, classify_monocratica)

        # -------------------------------------------------------------
        # 2. SENTENÇAS DE 1º GRAU (Prioridade 100)
        # -------------------------------------------------------------
        def match_sentenca(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if "sentenca" in doc_type:
                return True
            header = text[:350]
            # Se o cabeçalho indica explicitamente certidão, trânsito em julgado, ato ordinatório ou edital, não é sentença
            if re.search(
                r"\b(?:certid[aã]o|transito\s+em\s+julgado|ato\s+ordinat[oó]rio|edital\s+de)\b",
                header,
            ):
                return False
            if re.search(r"\bsenten[cç]a\b", header) and not re.search(
                r"\b(?:da|daquela|r\.)\s+senten[cç]a\b", header
            ):
                return True
            # Se não há doc_type conflitante, verifica comando terminativo forte
            if doc_type in {"", "outro"} and re.search(
                r"\bjulgo\s+(?:procedente|improcedente|parcialmente|extinto)\b", text
            ):
                return True
            return False

        def classify_sentenca(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            tags = ["primeiro_grau", "ato_decisorio"]

            # Registra menções incidentais como tags sem alterar a categoria
            if "edital" in text:
                tags.append("contem_mencao_edital")
            if "intimacao" in text or "intimad" in text:
                tags.append("contem_intimacao_partes")

            if "homologo o acordo" in text or "homologacao de acordo" in text:
                tags.extend(["autocomposicao", "acordo", "extincao_com_merito"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.SENTENCA,
                    specific_category="SENTENCA_HOMOLOGATORIA_ACORDO",
                    tags=tags,
                    confidence=0.98,
                )
            if (
                "art. 485" in text
                or "sem resolucao do merito" in text
                or "sem julgamento do merito" in text
            ):
                tags.extend(["terminativa", "sem_merito", "art_485_cpc"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.SENTENCA,
                    specific_category="SENTENCA_EXTINTIVA_SEM_MERITO",
                    tags=tags,
                    confidence=0.96,
                )
            if "julgo procedente" in text and "improcedente" not in text:
                tags.extend(["merito", "procedencia_total"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.SENTENCA,
                    specific_category="SENTENCA_PROCEDENCIA",
                    tags=tags,
                    confidence=0.97,
                )
            if "julgo improcedente" in text:
                tags.extend(["merito", "improcedencia_total"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.SENTENCA,
                    specific_category="SENTENCA_IMPROCEDENCIA",
                    tags=tags,
                    confidence=0.97,
                )
            if "julgo parcialmente procedente" in text:
                tags.extend(["merito", "parcial_procedencia", "sucumbencia_reciproca"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.SENTENCA,
                    specific_category="SENTENCA_PARCIAL_PROCEDENCIA",
                    tags=tags,
                    confidence=0.96,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.SENTENCA,
                specific_category="SENTENCA_MERITO_GENERICA",
                tags=tags,
                confidence=0.92,
            )

        self.register_rule("sentenca_specialized", 100, match_sentenca, classify_sentenca)

        # -------------------------------------------------------------
        # 3. ACÓRDÃOS COLEGIAIS (Prioridade 95)
        # -------------------------------------------------------------
        def match_acordao(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            # Decisões monocráticas já foram filtradas na prioridade 105
            if "acordao" in doc_type:
                return True
            header = text[:350]
            # Exige evidência colegiada clara: acórdão no cabeçalho ou "acordam os"
            return bool("acordam os" in text or re.search(r"\bacordao\b", header))

        def classify_acordao(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            classe = _normalize(meta.get("classe_processual") or meta.get("procedural_class"))
            tags = ["colegiado", "segundo_grau"]

            if "apelacao" in classe or "apelacao" in text[:400]:
                return TaxonomyClassification(
                    macro_category=MacroCategory.ACORDAO,
                    specific_category="ACORDAO_APELACAO",
                    tags=tags + ["merito_recursal"],
                    confidence=0.98,
                    cnj_class_hint="198",
                )
            if "agravo de instrumento" in classe or "agravo de instrumento" in text[:400]:
                return TaxonomyClassification(
                    macro_category=MacroCategory.ACORDAO,
                    specific_category="ACORDAO_AGRAVO_INSTRUMENTO",
                    tags=tags + ["tutela_recursal", "interlocutoria"],
                    confidence=0.98,
                    cnj_class_hint="202",
                )
            if "embargos de declaracao" in classe or "embargos de declaracao" in text[:400]:
                return TaxonomyClassification(
                    macro_category=MacroCategory.ACORDAO,
                    specific_category="ACORDAO_EMBARGOS_DECLARACAO",
                    tags=tags + ["integracao_julgamento"],
                    confidence=0.98,
                    cnj_class_hint="1689",
                )
            if (
                "especial" in classe
                or "extraordinario" in classe
                or "resp" in text[:300]
                or "stj" in text[:300]
            ):
                return TaxonomyClassification(
                    macro_category=MacroCategory.ACORDAO,
                    specific_category="ACORDAO_CORTE_SUPERIOR",
                    tags=tags + ["tribunal_superior", "precedente_qualificado"],
                    confidence=0.97,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.ACORDAO,
                specific_category="ACORDAO_COLEGIADO_GENERICO",
                tags=tags,
                confidence=0.92,
            )

        self.register_rule("acordao_specialized", 95, match_acordao, classify_acordao)

        # -------------------------------------------------------------
        # 4. DECISÕES INTERLOCUTÓRIAS E TUTELAS DE URGÊNCIA (Prioridade 90)
        # -------------------------------------------------------------
        def match_interlocutoria(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if (
                any(k in doc_type for k in ["decisao", "interlocutoria", "liminar"])
                and "monocratica" not in doc_type
            ):
                return True
            header = text[:350]
            return bool(
                re.search(r"\bdecisao\b", header)
                and not re.search(r"\bsentenca\b", header)
                and not re.search(r"\bmonocratica\b", header)
            )

        def classify_interlocutoria(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            classe = _normalize(meta.get("classe_processual") or meta.get("procedural_class"))
            tags = ["decisao_incidental"]

            if any(
                k in text
                for k in [
                    "tutela provisoria",
                    "tutela de urgencia",
                    "liminar",
                    "inaudita altera parte",
                ]
            ):
                tags.extend(["tutela_urgencia", "liminar", "periculum_in_mora"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.DECISAO_INTERLOCUTORIA,
                    specific_category="DECISAO_TUTELA_URGENCIA_LIMINAR",
                    tags=tags,
                    confidence=0.96,
                )
            if (
                "saneamento" in text
                or "fixo os pontos controvertidos" in text
                or "saneador" in text
            ):
                tags.extend(["saneamento", "organizacao_processual"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.DECISAO_INTERLOCUTORIA,
                    specific_category="DECISAO_SANEADORA",
                    tags=tags,
                    confidence=0.96,
                )
            if (
                "maria da penha" in classe
                or "medidas protetivas" in classe
                or "medida protetiva" in text
            ):
                tags.extend(["penal", "violencia_domestica", "cautelar"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.DECISAO_INTERLOCUTORIA,
                    specific_category="DECISAO_MEDIDA_PROTETIVA_CAUTELAR",
                    tags=tags,
                    confidence=0.97,
                )
            if (
                "prisao em flagrante" in classe
                or "custodia" in text
                or "liberdade provisoria" in text
            ):
                tags.extend(["penal", "liberdade", "flagrante"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.DECISAO_INTERLOCUTORIA,
                    specific_category="DECISAO_CRIMINAL_CUSTODIA",
                    tags=tags,
                    confidence=0.96,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.DECISAO_INTERLOCUTORIA,
                specific_category="DECISAO_INTERLOCUTORIA_GENERICA",
                tags=tags,
                confidence=0.88,
            )

        self.register_rule(
            "interlocutoria_specialized", 90, match_interlocutoria, classify_interlocutoria
        )

        # -------------------------------------------------------------
        # 5. EDITAIS (Prioridade 85) - Exige veículo de edital formal
        # -------------------------------------------------------------
        def match_edital(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if "edital" in doc_type:
                return True
            # Se não é ato decisório conhecido, verifica cabeçalho formal
            header = text[:350]
            return bool(doc_type in {"", "outro"} and re.search(r"\bedital\s+de\b", header))

        def classify_edital(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            tags = ["edital"]
            if "leilao" in text or "praca" in text or "alienacao" in text:
                tags.extend(["leilao", "alienacao_judicial"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.EDITAL,
                    specific_category="EDITAL_LEILAO_PRACA",
                    tags=tags,
                    confidence=0.98,
                )
            if "citacao" in text:
                tags.extend(["citacao", "reu_incerto"])
                prazo_m = re.search(r"prazo[:\s]+(\d+)\s*dias", text)
                if prazo_m:
                    tags.append(f"prazo_{prazo_m.group(1)}d")
                return TaxonomyClassification(
                    macro_category=MacroCategory.EDITAL,
                    specific_category="EDITAL_CITACAO",
                    tags=tags,
                    confidence=0.99,
                )
            if "intimacao" in text:
                tags.extend(["intimacao", "publicidade"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.EDITAL,
                    specific_category="EDITAL_INTIMACAO",
                    tags=tags,
                    confidence=0.95,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.EDITAL,
                specific_category="EDITAL_GENERICO",
                tags=tags,
                confidence=0.90,
            )

        self.register_rule("edital_specialized", 85, match_edital, classify_edital)

        # -------------------------------------------------------------
        # 6. ATOS DE COMUNICAÇÃO / INTIMAÇÃO / CITAÇÃO DIRETA (Prioridade 80)
        # -------------------------------------------------------------
        def match_comunicacao(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if any(k in doc_type for k in ["intimacao", "citacao", "notificacao", "comunicacao"]):
                return True
            # Cabeçalho formal do diário (não mera menção de intimação no fim da sentença)
            header = text[:350]
            return bool(
                doc_type in {"", "outro"}
                and (
                    re.search(r"\bintimacao\s+(?:de|por|para|do|da|acerca)\b", header)
                    or re.search(r"\baviso\s+de\s+intimacao\b", header)
                    or re.search(r"\bficam?\s+.*?\s+intimad[ao][s]?\b", header)
                )
            )

        def classify_comunicacao(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            tags = ["comunicacao_processual"]
            if "audiencia" in text or "conciliacao" in text or "instrucao" in text:
                tags.extend(["audiencia", "pauta"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.PUBLICACAO_COMUNICACAO,
                    specific_category="INTIMACAO_AUDIENCIA",
                    tags=tags,
                    confidence=0.96,
                )
            if (
                "art. 523" in text
                or "cumprimento de sentenca" in text
                or "pagamento voluntario" in text
            ):
                tags.extend(["execucao", "pagamento", "art_523_cpc"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.PUBLICACAO_COMUNICACAO,
                    specific_category="INTIMACAO_PAGAMENTO_CUMPRIMENTO",
                    tags=tags,
                    confidence=0.95,
                )
            if "contrarrazoes" in text or "apresentar resposta" in text or "recurso" in text:
                tags.extend(["recurso", "contraditorio"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.PUBLICACAO_COMUNICACAO,
                    specific_category="INTIMACAO_CONTRARRAZOES_RECURSO",
                    tags=tags,
                    confidence=0.94,
                )
            if "pericia" in text or "perito" in text:
                tags.extend(["prova_pericial"])
                return TaxonomyClassification(
                    macro_category=MacroCategory.PUBLICACAO_COMUNICACAO,
                    specific_category="INTIMACAO_PERICIA",
                    tags=tags,
                    confidence=0.92,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.PUBLICACAO_COMUNICACAO,
                specific_category="INTIMACAO_GENERICA",
                tags=tags,
                confidence=0.90,
            )

        self.register_rule("comunicacao_specialized", 80, match_comunicacao, classify_comunicacao)

        # -------------------------------------------------------------
        # 7. ATOS CARTORÁRIOS E CERTIDÕES (Prioridade 75)
        # -------------------------------------------------------------
        def match_cartorio(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if any(k in doc_type for k in ["certidao", "ato ordinatorio", "juntada"]):
                return True
            header = text[:350]
            return bool(
                doc_type in {"", "outro"}
                and (
                    re.search(r"\bato\s+ordinatorio\b", header)
                    or re.search(r"\bcertifico\s+e\s+dou\s+fe\b", header)
                    or re.search(r"\bcertidao\s+de\s+transito\s+em\s+julgado\b", header)
                )
            )

        def classify_cartorio(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            if "transito em julgado" in text:
                return TaxonomyClassification(
                    macro_category=MacroCategory.ATO_CARTORARIO,
                    specific_category="CERTIDAO_TRANSITO_JULGADO",
                    tags=["coisa_julgada", "definitivo"],
                    confidence=0.98,
                )
            if "ato ordinatorio" in text:
                return TaxonomyClassification(
                    macro_category=MacroCategory.ATO_CARTORARIO,
                    specific_category="ATO_ORDINATORIO_SECRETARIA",
                    tags=["expediente_cartorio", "sem_cunho_decisorio"],
                    confidence=0.95,
                )
            return TaxonomyClassification(
                macro_category=MacroCategory.ATO_CARTORARIO,
                specific_category="CERTIDAO_CARTORARIA",
                tags=["certidao"],
                confidence=0.90,
            )

        self.register_rule("cartorio_specialized", 75, match_cartorio, classify_cartorio)

        # -------------------------------------------------------------
        # 8. DESPACHOS DE MERO EXPEDIENTE (Prioridade 60)
        # -------------------------------------------------------------
        def match_despacho(text: str, meta: dict[str, Any]) -> bool:
            doc_type = _normalize(meta.get("doc_type") or meta.get("document_type"))
            if "despacho" in doc_type:
                return True
            header = text[:350]
            return bool(re.search(r"\bdespacho\b", header))

        def classify_despacho(text: str, meta: dict[str, Any]) -> TaxonomyClassification:
            return TaxonomyClassification(
                macro_category=MacroCategory.DESPACHO,
                specific_category="DESPACHO_MERO_EXPEDIENTE",
                tags=["impulso_processual", "sem_conteudo_decisorio"],
                confidence=0.95,
            )

        self.register_rule("despacho_specialized", 60, match_despacho, classify_despacho)
