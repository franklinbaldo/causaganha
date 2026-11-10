"""Esteira de Descoberta Aberta, Síntese e Julgamento de Regexes (Open NER Tournament).

Implementa o ciclo em 3 estágios guiado por IA:
1. Thx 1 (Explorador Aberto): Descobre entidades e obrigações sem taxonomia pré-fixada.
2. Thx 2 (Engenheiro de Regex): Sintetiza expressões regulares com grupos de captura e travas negativas.
3. Thx 3 / Juiz (Adjudicador & Catraca): Julga o resultado das regexes em dados reais,
   descartando candidatos de baixa precisão e promovendo apenas os melhores para o catálogo oficial.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any

from causaganha.decisoes.regex_tournament import CompetitiveRegex, RegexTournament


class OpenNerParseError(ValueError):
    """Erro ao processar respostas da esteira Open NER."""


class OpenNerListExpectedError(OpenNerParseError):
    """Resposta de descoberta deve ser uma lista JSON."""


@dataclass
class DiscoveredEntity:
    """Entidade aberta descoberta pelo Thx Explorador."""

    entity_type: str
    literal: str
    context_snippet: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdjudicationVerdict:
    """Veredito emitido pelo Juiz sobre a qualidade da extração de uma regex."""

    is_valid: bool
    quality_score: float  # 0.0 a 1.0
    is_clean_capture: bool
    reason: str
    tested_literal: str
    extracted_literal: str


@dataclass
class NerTournamentRanking:
    """Ranking das melhores regexes selecionadas pelo Juiz para cada entidade descoberta."""

    entity_type: str
    top_rules: list[dict[str, Any]]
    total_evaluated: int
    leader_pattern_id: str | None


class OpenNerTournamentManager:
    """Orquestrador do ciclo completo: Descoberta Aberta -> Síntese -> Julgamento -> Top-K."""

    def __init__(self, top_k: int = 3, min_precision: float = 0.90):
        self.top_k = top_k
        self.min_precision = min_precision
        self.tournaments: dict[str, RegexTournament] = {}

    # =========================================================================
    # ESTÁGIO 1: Thx 1 — O Explorador Aberto (Zero-Shot Discovery)
    # =========================================================================

    @staticmethod
    def build_discovery_prompt(passage_text: str) -> str:
        """Constrói o prompt aberto para o Thx identificar qualquer entidade jurídica relevante."""
        return f"""Você é um especialista em jurimetria e análise de atos judiciais brasileiros.
Examine o trecho judicial abaixo de forma ABERTA, sem se restringir a categorias pré-definidas.

Identifique e extraia todas as entidades, determinações fáticas, prazos, penalidades, obrigações ou parâmetros relevantes:
\"\"\"{passage_text.strip()}\"\"\"

Instruções:
- Identifique termos específicos como: prazos, limites de multa (astreintes), índices de correção, tipos de obrigação, termos contratuais, benefícios legais, etc.
- Retorne APENAS um array JSON no formato:
[
  {{
    "entity_type": "NOME_EM_MAIUSCULAS_E_SNAKE_CASE",
    "literal": "trecho exato encontrado no texto",
    "attributes": {{ "explicacao": "justificativa sucinta" }}
  }}
]
""".strip()

    @staticmethod
    def parse_discovery_response(
        response_text: str, context_snippet: str = ""
    ) -> list[DiscoveredEntity]:
        """Extrai as entidades descobertas a partir da resposta do modelo."""
        text = response_text.strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)

        try:
            items = json.loads(text)
        except (json.JSONDecodeError, ValueError) as err:
            msg = f"Erro ao decodificar JSON de entidades descobertas: {err}"
            raise OpenNerParseError(msg) from err

        if not isinstance(items, list):
            raise OpenNerListExpectedError

        results: list[DiscoveredEntity] = []
        for item in items:
            if isinstance(item, dict) and "entity_type" in item and "literal" in item:
                results.append(
                    DiscoveredEntity(
                        entity_type=str(item["entity_type"]).upper().strip(),
                        literal=str(item["literal"]).strip(),
                        context_snippet=context_snippet or str(item["literal"]),
                        attributes=item.get("attributes", {}),
                    )
                )
        return results

    # =========================================================================
    # ESTÁGIO 2: Thx 2 — O Engenheiro de Regex (Synthesis)
    # =========================================================================

    @staticmethod
    def build_synthesis_prompt(entity: DiscoveredEntity, broader_context: str = "") -> str:
        """Gera o prompt para o Thx Engenheiro criar uma regex para a entidade descoberta."""
        ctx = broader_context or entity.context_snippet
        return f"""Você é um engenheiro de compiladores e expressões regulares de altíssima precisão.
Precisamos de uma Python regex para capturar a entidade '{entity.entity_type}'.

Exemplo real encontrado no texto:
- Texto literal: "{entity.literal}"
- Contexto de ocorrência: \"\"\"{ctx}\"\"\"

Requisitos técnicos obrigatórios:
1. Use limites de palavra (\\b) e suporte pequenas flexões gramaticais (plural, gênero, pontuação de moeda).
2. Adicione 'negative_pattern' com travas de exclusão para evitar que a regex capture falso positivo.
3. Se houver valor ou dado extraível, use grupos de captura nomeados ou numerados.
4. Retorne APENAS um objeto JSON:
{{
  "pattern": "r\\"expressão principal\\"",
  "negative_pattern": "r\\"expressão de trava ou vazio\\"",
  "capture_group": 1,
  "explanation": "justificativa técnica"
}}
""".strip()

    @staticmethod
    def parse_synthesis_response(
        response_text: str,
        entity_type: str,
        pattern_id: str | None = None,
    ) -> CompetitiveRegex:
        """Converte a resposta do Thx Engenheiro em uma CompetitiveRegex pronta para torneio."""
        text = response_text.strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)

        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, ValueError) as err:
            msg = f"Erro ao decodificar JSON de síntese de regex: {err}"
            raise OpenNerParseError(msg) from err

        raw_pattern = str(payload.get("pattern", "")).strip()
        if raw_pattern.startswith(('r"', "r'")) and raw_pattern.endswith(('"', "'")):
            raw_pattern = raw_pattern[2:-1]

        raw_neg = payload.get("negative_pattern")
        if raw_neg:
            raw_neg = str(raw_neg).strip()
            if raw_neg.startswith(('r"', "r'")) and raw_neg.endswith(('"', "'")):
                raw_neg = raw_neg[2:-1]
            if not raw_neg:
                raw_neg = None

        try:
            re.compile(raw_pattern)
            if raw_neg:
                re.compile(raw_neg)
        except re.error as err:
            msg = f"Regex inválida retornada pelo modelo: {err}"
            raise OpenNerParseError(msg) from err

        pid = (
            pattern_id
            or f"ner_{entity_type.lower()}_{re.sub(r'[^a-zA-Z0-9]', '', raw_pattern)[:12]}"
        )

        return CompetitiveRegex(
            pattern_id=pid,
            pattern=raw_pattern,
            category=entity_type.lower(),
            source="thx_ner_engineer",
            description=str(payload.get("explanation", "")),
            negative_pattern=raw_neg,
        )

    # =========================================================================
    # ESTÁGIO 3: O Juiz — Adjudicação, Julgamento e Seleção dos Melhores
    # =========================================================================

    @staticmethod
    def adjudicate_candidate_extraction(
        candidate_rule: CompetitiveRegex,
        sample_text: str,
        expected_target: str,
    ) -> AdjudicationVerdict:
        """Julga se a regex capturou o valor exato pretendido sem ruído ou contaminação."""
        if not candidate_rule.matches(sample_text):
            return AdjudicationVerdict(
                is_valid=False,
                quality_score=0.0,
                is_clean_capture=False,
                reason="A regex não deu match no texto de teste.",
                tested_literal=expected_target,
                extracted_literal="",
            )

        match = candidate_rule.compiled.search(sample_text)
        if not match:
            return AdjudicationVerdict(
                is_valid=False,
                quality_score=0.0,
                is_clean_capture=False,
                reason="Match rejeitado por travas negativas ou ausente.",
                tested_literal=expected_target,
                extracted_literal="",
            )

        extracted_raw = match.group(0).strip()
        expected_clean = expected_target.strip().lower()
        extracted_clean = extracted_raw.lower()

        # Verifica se o trecho esperado está contido no match ou coincide
        if expected_clean in extracted_clean or extracted_clean in expected_clean:
            len_ratio = len(expected_clean) / max(len(extracted_clean), 1)
            # Se capturou muito mais do que devia (ex: frase inteira em vez do valor), score cai
            is_clean = len_ratio >= 0.50
            score = round(min(1.0, len_ratio), 2)
            return AdjudicationVerdict(
                is_valid=True,
                quality_score=score,
                is_clean_capture=is_clean,
                reason="Captura validada com sucesso pelo Juiz."
                if is_clean
                else "Captura excessiva (ruído contextual).",
                tested_literal=expected_target,
                extracted_literal=extracted_raw,
            )

        return AdjudicationVerdict(
            is_valid=False,
            quality_score=0.2,
            is_clean_capture=False,
            reason=f"Capturou trecho divergente: '{extracted_raw}' em vez de '{expected_target}'.",
            tested_literal=expected_target,
            extracted_literal=extracted_raw,
        )

    def judge_and_promote(
        self,
        candidate_rule: CompetitiveRegex,
        validation_dataset: list[dict[str, Any]],
        text_key: str = "texto",
        expected_target_key: str = "target_literal",
    ) -> dict[str, Any]:
        """Avalia a regex contra um lote de validação e só promove as melhores (Top-K)."""
        cat = candidate_rule.category.lower().strip()
        if cat not in self.tournaments:
            self.tournaments[cat] = RegexTournament(
                top_k=self.top_k, min_precision=self.min_precision
            )

        tournament = self.tournaments[cat]

        tp = 0
        fp = 0
        total_targets = len(validation_dataset)

        for doc in validation_dataset:
            text = doc.get(text_key, "")
            expected = doc.get(expected_target_key)
            if not text:
                continue

            verdict = self.adjudicate_candidate_extraction(candidate_rule, text, expected or "")
            if expected:
                if verdict.is_valid and verdict.is_clean_capture:
                    tp += 1
                else:
                    fp += 1
            else:
                # Documento de controle negativo (não deveria ter essa entidade)
                if candidate_rule.matches(text):
                    fp += 1

        candidate_rule.update_metrics(tp=tp, fp=fp, total_positives_in_dataset=total_targets)

        # Regra de Julgamento: só é promovida se passar na catraca estrita
        if candidate_rule.precision >= self.min_precision and fp <= 1 and tp > 0:
            candidate_rule.status = "PROMOTED"
            registered = tournament.register(
                pattern=candidate_rule.pattern,
                category=cat,
                pattern_id=candidate_rule.pattern_id,
                source=candidate_rule.source,
                description=candidate_rule.description,
                negative_pattern=candidate_rule.negative_pattern,
            )
            registered.status = "PROMOTED"
            registered.precision = candidate_rule.precision
            registered.tp = candidate_rule.tp
            registered.fp = candidate_rule.fp
            registered.score = candidate_rule.score
            promoted = True
            judgment_summary = (
                f"APROVADA PELO JUIZ: Precisão {candidate_rule.precision * 100:.1f}% ({tp} acertos, {fp} erros). "
                f"Promovida para o Top-{self.top_k} de '{cat.upper()}'."
            )
        else:
            candidate_rule.status = "REJECTED" if fp > 2 else "DEMOTED"
            promoted = False
            judgment_summary = (
                f"REJEITADA PELO JUIZ: Precisão insuficiente ({candidate_rule.precision * 100:.1f}%) "
                f"ou excesso de falsos positivos ({fp} erros). Descartada."
            )

        return {
            "entity_type": cat,
            "pattern_id": candidate_rule.pattern_id,
            "promoted": promoted,
            "status": candidate_rule.status,
            "tp": tp,
            "fp": fp,
            "precision": candidate_rule.precision,
            "score": candidate_rule.score,
            "judgment": judgment_summary,
        }

    def get_best_regexes(self, entity_type: str) -> list[CompetitiveRegex]:
        """Retorna apenas as melhores regexes aprovadas pelo Juiz para a entidade."""
        cat = entity_type.lower().strip()
        t = self.tournaments.get(cat)
        if not t:
            return []
        return t.get_top_k(cat)
