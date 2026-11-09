"""Segmentador Estrutural Completo de Decisões Judiciais Brasileiras.

Decompõe o documento judicial em suas seções canônicas:
- CABECALHO (identificação, tribunal, vara, partes, advogados)
- EMENTA (tese jurídica e resumo em acórdãos)
- RELATORIO (histórico processual ou menção de dispensa)
- FUNDAMENTACAO / VOTO (argumentação jurídica, teses, preliminares e mérito)
- DISPOSITIVO / DECISORIO (resultado de mérito, condenações e desfecho)
- HONORARIOS_CUSTAS (sucumbência, custas e verba advocatícia)
- ENCERRAMENTO (data, localidade, assinatura do magistrado, certidão e P.R.I.)

Utiliza roteamento por metadados (TopologyRouter) e decodificação sequencial
com restrições de ordem jurídica (Dynamic Programming / Gramática Monotônica).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any

from causaganha.decisoes.topology_router import DecisionTopology, TopologyRouter


class SectionType(str, enum.Enum):
    CABECALHO = "CABECALHO"
    EMENTA = "EMENTA"
    RELATORIO = "RELATORIO"
    FUNDAMENTACAO = "FUNDAMENTACAO"
    VOTO = "VOTO"
    DISPOSITIVO = "DISPOSITIVO"
    HONORARIOS_CUSTAS = "HONORARIOS_CUSTAS"
    ENCERRAMENTO = "ENCERRAMENTO"


@dataclass
class SectionSpan:
    section_type: SectionType
    start: int
    end: int
    text: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_type": self.section_type.value,
            "start": self.start,
            "end": self.end,
            "char_count": len(self.text),
            "confidence": round(self.confidence, 4),
            "text": self.text,
        }


@dataclass
class DocumentStructure:
    topology: DecisionTopology
    sections: dict[str, SectionSpan]
    entities: dict[str, Any]
    metadata_used: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology": self.topology.value,
            "metadata": self.metadata_used,
            "entities": self.entities,
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
        }


# Expressões canônicas para ancoragem estrutural
ANCHORS_CABECALHO = re.compile(
    r"\b(?:poder\s+judici[aá]rio|tribunal\s+de\s+justi[cç]a|comarca\s+de|vara\s+c[ií]vel|juizado\s+especial|processo\s+n[ºo]|origem:|sess[aã]o\s+eletr[oô]nica)\b",
    re.IGNORECASE,
)

ANCHORS_EMENTA = re.compile(
    r"\b(?:ementa\s*:|ementa\s+estruturada|apela[cç][aã]o\s+c[ií]vel\b|direito\s+do\s+consumidor|direito\s+civil|direito\s+banc[aá]rio)\b",
    re.IGNORECASE,
)

ANCHORS_RELATORIO = re.compile(
    r"\b(?:relat[oó]rio\s*:|relat[oó]rio\b|trata-se\s+de|vistos(?:\s+etc)?\b|relat[oó]rio\s+dispensado)\b",
    re.IGNORECASE,
)

ANCHORS_FUNDAMENTACAO = re.compile(
    r"\b(?:fundamenta[cç][aã]o\s*:|fundamenta[cç][aã]o\b|do\s+m[eé]rito\s*:|m[eé]rito\s*:|passo\s+a\s+(?:decidir|julgar)|decido\b|raz[oõ]es\s+de\s+decidir)\b",
    re.IGNORECASE,
)

ANCHORS_VOTO = re.compile(
    r"\b(?:voto\s*:|voto\b|passo\s+ao\s+voto|[eé]\s+como\s+voto|o\s+senhor\s+desembargador|voto\s+do\s+relator)\b",
    re.IGNORECASE,
)

ANCHORS_DISPOSITIVO = re.compile(
    r"\b(?:dispositivo\s*:|dispositivo\b|ante\s+(?:ao|o)\s+exposto|diante\s+do\s+exposto|isto\s+posto|pelo\s+exposto|julgo\s+(?:procedente|improcedente|parcialmente|extinto)|acordam\s+os\s+desembargadores|homologo\s+o\s+acordo|dou\s+provimento|nego\s+provimento)\b",
    re.IGNORECASE,
)

ANCHORS_HONORARIOS = re.compile(
    r"\b(?:honor[aá]rios\s+(?:advocat[ií]cios|sucumbenciais)|custas\s+processuais|sem\s+custas|justi[cç]a\s+gratuita|sucumb[eê]ncia\s+rec[ií]proca|condeno\s+ao\s+pagamento\s+d[ae]s\s+custas)\b",
    re.IGNORECASE,
)

ANCHORS_ENCERRAMENTO = re.compile(
    r"\b(?:publique-se|registre-se|intimem-se|p\.r\.i\.|juiz(?:a)?\s+de\s+direito|desembargador(?:a)?|porto\s+velho|s[aã]o\s+paulo|salvador|assinado\s+digitalmente)\b",
    re.IGNORECASE,
)


class FullDocumentStructuralSegmenter:
    """Decompõe o documento judicial em suas seções canônicas de forma completa."""

    def __init__(self, router: type[TopologyRouter] = TopologyRouter):
        self.router = router

    @staticmethod
    def split_units(text: str) -> list[dict[str, Any]]:
        """Divide o texto em frases ou parágrafos preservando posições originais."""
        if text.count("\n") >= 3:
            matches = list(re.finditer(r"[^\n]+(?:\n|$)", text))
        else:
            matches = list(re.finditer(r"[^.!?\n]+(?:[.!?\n]+|\s*$)", text))

        units = []
        for m in matches:
            t = m.group(0).strip()
            if t:
                units.append({"text": t, "start": m.start(), "end": m.end()})
        if not units:
            units = [{"text": text.strip(), "start": 0, "end": len(text)}]
        return units

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extrai entidades-chave do documento (valores em R$, CNJ, partes)."""
        entities: dict[str, Any] = {}

        # 1. Valores monetários em condenações
        val_matches = re.findall(r"R\$\s*[\d.]+(?:,\d{2})?", text)
        if val_matches:
            entities["valores_monetarios"] = list(dict.fromkeys(val_matches))

        # 2. Número de processo no padrão CNJ
        cnj_match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", text)
        if cnj_match:
            entities["numero_cnj"] = cnj_match.group(0)

        # 3. Dispositivos legais mais citados
        art_matches = re.findall(
            r"\bart\w*\.?\s*\d+[^,\n;]+(?:cpc|cc|cdc|clt|cpp|cp)", text, re.IGNORECASE
        )
        if art_matches:
            entities["fundamentacao_legal"] = list(
                dict.fromkeys([a.strip() for a in art_matches[:5]])
            )

        return entities

    def segment(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentStructure:
        """Executa a decomposição estrutural completa da decisão."""
        meta = dict(metadata or {})
        topology = self.router.route(meta, text=text)

        units = self.split_units(text)
        total_units = len(units)

        # Gramática sequencial esperada por topologia
        if topology == DecisionTopology.ACORDAO:
            expected_flow = [
                SectionType.CABECALHO,
                SectionType.EMENTA,
                SectionType.RELATORIO,
                SectionType.VOTO,
                SectionType.DISPOSITIVO,
                SectionType.ENCERRAMENTO,
            ]
        elif topology == DecisionTopology.EXECUCAO:
            expected_flow = [
                SectionType.CABECALHO,
                SectionType.FUNDAMENTACAO,
                SectionType.DISPOSITIVO,
                SectionType.HONORARIOS_CUSTAS,
                SectionType.ENCERRAMENTO,
            ]
        else:
            # Sentença Padrão de 1º Grau
            expected_flow = [
                SectionType.CABECALHO,
                SectionType.RELATORIO,
                SectionType.FUNDAMENTACAO,
                SectionType.DISPOSITIVO,
                SectionType.HONORARIOS_CUSTAS,
                SectionType.ENCERRAMENTO,
            ]

        # Pontuação de cada unidade para cada tipo de seção
        unit_scores: list[dict[SectionType, float]] = []

        for idx, u in enumerate(units):
            scores: dict[SectionType, float] = {st: 0.05 for st in SectionType}
            u_text = u["text"]
            pos_ratio = idx / max(total_units - 1, 1)

            # Heurísticas de Posição
            if pos_ratio < 0.20:
                scores[SectionType.CABECALHO] += 0.40
                scores[SectionType.EMENTA] += 0.35
            elif pos_ratio < 0.45:
                scores[SectionType.RELATORIO] += 0.30
                scores[SectionType.FUNDAMENTACAO] += 0.25
                scores[SectionType.VOTO] += 0.25
            elif pos_ratio < 0.75:
                scores[SectionType.FUNDAMENTACAO] += 0.40
                scores[SectionType.VOTO] += 0.40
            else:
                scores[SectionType.DISPOSITIVO] += 0.45
                scores[SectionType.HONORARIOS_CUSTAS] += 0.35
                scores[SectionType.ENCERRAMENTO] += 0.30

            # Âncoras Textuais Fortes
            if ANCHORS_CABECALHO.search(u_text) and pos_ratio < 0.30:
                scores[SectionType.CABECALHO] += 0.60
            if ANCHORS_EMENTA.search(u_text) and pos_ratio < 0.40:
                scores[SectionType.EMENTA] += 0.70
            if ANCHORS_RELATORIO.search(u_text):
                scores[SectionType.RELATORIO] += 0.65
            if ANCHORS_FUNDAMENTACAO.search(u_text):
                scores[SectionType.FUNDAMENTACAO] += 0.65
            if ANCHORS_VOTO.search(u_text):
                scores[SectionType.VOTO] += 0.65
            if ANCHORS_DISPOSITIVO.search(u_text) and pos_ratio > 0.30:
                scores[SectionType.DISPOSITIVO] += 0.80
            if ANCHORS_HONORARIOS.search(u_text) and pos_ratio > 0.50:
                scores[SectionType.HONORARIOS_CUSTAS] += 0.60
            if ANCHORS_ENCERRAMENTO.search(u_text) and pos_ratio > 0.60:
                scores[SectionType.ENCERRAMENTO] += 0.60

            unit_scores.append(scores)

        # Decodificador Sequencial Monotônico (Dynamic Programming / Viterbi)
        # Garante que a ordem das seções seja estritamente respeitada
        k_states = len(expected_flow)
        dp = [[-1e9] * k_states for _ in range(total_units)]
        parent = [[-1] * k_states for _ in range(total_units)]

        # Inicializa primeira unidade (geralmente CABECALHO ou primeiro estado)
        for s in range(min(2, k_states)):
            st = expected_flow[s]
            dp[0][s] = unit_scores[0][st]

        for i in range(1, total_units):
            for cur_s in range(k_states):
                cur_type = expected_flow[cur_s]
                emit = unit_scores[i][cur_type]

                # Pode permanecer no mesmo estado ou avançar para estados posteriores
                best_prev_val = -1e9
                best_prev_s = -1
                for prev_s in range(cur_s + 1):
                    # Pequena penalidade de transição para incentivar continuidade de blocos
                    trans_penalty = 0.0 if prev_s == cur_s else -0.15
                    val = dp[i - 1][prev_s] + emit + trans_penalty
                    if val > best_prev_val:
                        best_prev_val = val
                        best_prev_s = prev_s

                dp[i][cur_s] = best_prev_val
                parent[i][cur_s] = best_prev_s

        # Backtracking do caminho ótimo
        best_last_state = int(max(range(k_states), key=lambda s: dp[total_units - 1][s]))
        state_path = [best_last_state]
        for i in range(total_units - 1, 0, -1):
            best_last_state = parent[i][best_last_state]
            state_path.append(best_last_state)
        state_path.reverse()

        # Agrupa unidades em seções contíguas
        sections: dict[str, SectionSpan] = {}
        cur_section_type = expected_flow[state_path[0]]
        cur_start = units[0]["start"]
        cur_end = units[0]["end"]
        cur_scores = [unit_scores[0][cur_section_type]]

        for i in range(1, total_units):
            st = expected_flow[state_path[i]]
            if st == cur_section_type:
                cur_end = units[i]["end"]
                cur_scores.append(unit_scores[i][st])
            else:
                # Salva seção anterior
                sec_name = cur_section_type.value.lower()
                sec_text = text[cur_start:cur_end].strip()
                if sec_text:
                    sections[sec_name] = SectionSpan(
                        section_type=cur_section_type,
                        start=cur_start,
                        end=cur_end,
                        text=sec_text,
                        confidence=float(sum(cur_scores) / max(len(cur_scores), 1)),
                    )
                # Inicia nova seção
                cur_section_type = st
                cur_start = units[i]["start"]
                cur_end = units[i]["end"]
                cur_scores = [unit_scores[i][st]]

        # Salva última seção
        sec_name = cur_section_type.value.lower()
        sec_text = text[cur_start:cur_end].strip()
        if sec_text:
            sections[sec_name] = SectionSpan(
                section_type=cur_section_type,
                start=cur_start,
                end=cur_end,
                text=sec_text,
                confidence=float(sum(cur_scores) / max(len(cur_scores), 1)),
            )

        # Extrai entidades estruturadas
        entities = self._extract_entities(text)

        return DocumentStructure(
            topology=topology,
            sections=sections,
            entities=entities,
            metadata_used=meta,
        )
