"""Catraca e Flywheel de Evolução Contínua do Torneio de Regexes.

Integra geração de expressões regulares (via LLM/Thx ou heurísticas de síntese)
com um gate estrito de promoção (Ratchet):
- Gera prompts especializados para o Thx/LLM propor padrões com travas negativas.
- Extrai e compila candidatos com validação estrita de sintaxe.
- Avalia contra benchmark ouro: só promove se precisão >= 90% e Falsos Positivos controlados.
- Rebaixa automaticamente padrões que perdem precisão com novos acórdãos/sentenças.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from causaganha.decisoes.regex_tournament import CompetitiveRegex, RegexTournament


class ThxParseError(ValueError):
    """Erro ao processar resposta do Thx."""


class InvalidRegexPatternError(ValueError):
    """Erro de sintaxe em expressão regular proposta."""


@dataclass
class GateResult:
    """Resultado da submissão de uma regex candidata ao portão de promoção."""

    promoted: bool
    status: str  # PROMOTED, CANDIDATE, DEMOTED, REJECTED
    precision: float
    recall: float
    tp: int
    fp: int
    score: float
    reason: str
    candidate_id: str


class TournamentRatchet:
    """Controlador da catraca de promoção e geração evolutiva de regexes."""

    def __init__(
        self,
        tournament: RegexTournament | None = None,
        min_precision: float = 0.90,
        max_allowed_fp: int = 1,
    ):
        self.tournament = tournament or RegexTournament()
        self.min_precision = min_precision
        self.max_allowed_fp = max_allowed_fp

    @staticmethod
    def build_thx_prompt(
        decision_text: str,
        expected_category: str,
        failed_on: str | None = None,
        dispositivo_text: str | None = None,
    ) -> str:
        """Gera o prompt estruturado para o Thx/LLM propor uma nova regex cirúrgica."""
        sample_context = dispositivo_text or decision_text[:1200]
        failed_clause = (
            f"\nNota: A decisão foi erroneamente classificada como '{failed_on}' anteriormente."
            if failed_on
            else ""
        )

        prompt = f"""Você é um engenheiro sênior de processamento de linguagem natural e jurimetria brasileira.
Precisamos de uma expressão regular (Python regex) de altíssima precisão para identificar a categoria '{expected_category.upper()}'.{failed_clause}

Trecho relevante da decisão (Dispositivo/Conclusão):
\"\"\"{sample_context}\"\"\"

Instruções para a regex:
1. Deve capturar a fórmula dispositiva com foco em verbos judiciais (ex: julgo, acolho, extingo, homologo).
2. Deve incluir travas negativas ('negative_pattern') para evitar falsos positivos (ex: não confundir 'procedente' com 'procedente em parte' ou 'improcedente').
3. Retorne APENAS um objeto JSON com o formato:
{{
  "pattern": "r\\"expressão principal\\"",
  "negative_pattern": "r\\"expressão de exclusão ou vazio\\"",
  "scope": "dispositivo",
  "explanation": "justificativa sucinta"
}}
"""
        return prompt.strip()

    @staticmethod
    def parse_thx_candidate(
        response_text: str,
        category: str,
        pattern_id: str | None = None,
        source: str = "thx_generated",
    ) -> CompetitiveRegex:
        """Extrai a regex do retorno estruturado do modelo."""
        text = response_text.strip()
        # Remove eventuais blocos de código markdown
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)

        try:
            payload = json.loads(text)
        except (json.JSONDecodeError, ValueError) as err:
            msg = f"Não foi possível decodificar JSON da resposta do Thx: {err}"
            raise ThxParseError(msg) from err

        raw_pattern = str(payload.get("pattern", "")).strip()
        # Remove prefixos Python literais r"..." se presentes
        if raw_pattern.startswith(('r"', "r'")) and raw_pattern.endswith(('"', "'")):
            raw_pattern = raw_pattern[2:-1]

        raw_negative = payload.get("negative_pattern")
        if raw_negative:
            raw_negative = str(raw_negative).strip()
            if raw_negative.startswith(('r"', "r'")) and raw_negative.endswith(('"', "'")):
                raw_negative = raw_negative[2:-1]
            if not raw_negative:
                raw_negative = None

        scope = str(payload.get("scope", "all")).lower().strip()
        explanation = str(payload.get("explanation", ""))

        # Valida compilação antes de instanciar
        try:
            re.compile(raw_pattern)
            if raw_negative:
                re.compile(raw_negative)
        except re.error as err:
            msg = f"Expressão regular inválida retornada pelo modelo: {err}"
            raise InvalidRegexPatternError(msg) from err

        pid = (
            pattern_id
            or f"{category.lower().replace(' ', '_')}_{re.sub(r'[^a-zA-Z0-9]', '', raw_pattern)[:12]}"
        )

        return CompetitiveRegex(
            pattern_id=pid,
            pattern=raw_pattern,
            category=category,
            source=source,
            description=explanation,
            negative_pattern=raw_negative,
            scope=scope,
        )

    def gate_candidate(
        self,
        candidate: CompetitiveRegex,
        dataset: list[dict[str, Any]],
        text_key: str = "texto",
        label_key: str = "desfecho_cpc",
    ) -> GateResult:
        """Avalia um candidato contra o dataset e decide se ele é promovido ao torneio."""
        target_cat = candidate.category.lower().strip()
        tp = 0
        fp = 0
        total_positives = sum(
            1 for d in dataset if str(d.get(label_key, "")).lower().strip() == target_cat
        )

        for doc in dataset:
            text = doc.get(text_key, "")
            label = str(doc.get(label_key, "")).lower().strip()
            if not text:
                continue

            if candidate.matches(text):
                if label == target_cat:
                    tp += 1
                else:
                    fp += 1

        candidate.update_metrics(tp, fp, total_positives)

        # Regra da Catraca: para ser promovido diretamente, precisa de precisão >= 90% e FP <= max_allowed
        if candidate.precision >= self.min_precision and fp <= self.max_allowed_fp and tp > 0:
            candidate.status = "PROMOTED"
            # Registra no torneio ativo
            self.tournament.register(
                pattern=candidate.pattern,
                category=candidate.category,
                pattern_id=candidate.pattern_id,
                source=candidate.source,
                description=candidate.description,
                negative_pattern=candidate.negative_pattern,
                scope=candidate.scope,
            )
            return GateResult(
                promoted=True,
                status="PROMOTED",
                precision=candidate.precision,
                recall=candidate.recall,
                tp=tp,
                fp=fp,
                score=candidate.score,
                reason=f"Aprovado na catraca: precisão {candidate.precision * 100:.1f}% com apenas {fp} falso(s) positivo(s).",
                candidate_id=candidate.pattern_id,
            )

        status = "DEMOTED" if fp > self.max_allowed_fp else "CANDIDATE"
        return GateResult(
            promoted=False,
            status=status,
            precision=candidate.precision,
            recall=candidate.recall,
            tp=tp,
            fp=fp,
            score=candidate.score,
            reason=f"Reprovado na catraca: precisão {candidate.precision * 100:.1f}% ou excesso de falsos positivos ({fp} FP).",
            candidate_id=candidate.pattern_id,
        )

    @staticmethod
    def synthesize_dispositivo_candidate(
        dispositivo_snippet: str,
        category: str,
        pattern_id: str | None = None,
    ) -> CompetitiveRegex | None:
        """Sintetizador heurístico offline: deduz regex de alta precisão com trava negativa."""
        text = dispositivo_snippet.lower()
        cat = category.lower().strip()

        if cat == "procedente":
            if "procedente" in text and "parcial" not in text:
                pid = pattern_id or "proc_synth_procedente"
                return CompetitiveRegex(
                    pattern_id=pid,
                    pattern=r"\bjulgo\s+procedente(?:s)?\b",
                    category="procedente",
                    source="synthesizer",
                    negative_pattern=r"(?:parcialmente|em\s+parte|não|deixo\s+de|improcedente)",
                    scope="dispositivo",
                )
        elif cat == "parcialmente procedente":
            if "parcial" in text or "em parte" in text:
                pid = pattern_id or "parcial_synth_em_parte"
                return CompetitiveRegex(
                    pattern_id=pid,
                    pattern=r"\b(?:julgo\s+parcialmente\s+procedente|procedente\s+em\s+parte)\b",
                    category="parcialmente procedente",
                    source="synthesizer",
                    scope="dispositivo",
                )
        elif cat == "improcedente":
            if "improcedente" in text:
                pid = pattern_id or "improc_synth_improcedente"
                return CompetitiveRegex(
                    pattern_id=pid,
                    pattern=r"\bjulgo\s+improcedente(?:s)?\b",
                    category="improcedente",
                    source="synthesizer",
                    negative_pattern=r"(?:não\s+julgo|deixo\s+de)",
                    scope="dispositivo",
                )
        elif cat == "extinto sem mérito":
            if "485" in text or "sem resolução" in text:
                pid = pattern_id or "extinto_synth_485"
                return CompetitiveRegex(
                    pattern_id=pid,
                    pattern=r"\bextingo\s+o\s+processo\s+sem\s+resolução\b",
                    category="extinto sem mérito",
                    source="synthesizer",
                    negative_pattern=r"(?:afasto\s+a\s+extinção)",
                    scope="dispositivo",
                )
        elif cat == "acordo":
            if "acordo" in text or "homolog" in text:
                pid = pattern_id or "acordo_synth_homologo"
                return CompetitiveRegex(
                    pattern_id=pid,
                    pattern=r"\bhomologo\s+(?:o\s+)?acordo\b",
                    category="acordo",
                    source="synthesizer",
                    scope="dispositivo",
                )

        return None
