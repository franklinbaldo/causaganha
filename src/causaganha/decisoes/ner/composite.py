"""Orquestrador Composto de Entidades Judiciais Especializadas (Multi-Algorithm NER)."""

from __future__ import annotations

from typing import Any

from causaganha.decisoes.ner.cnj import CnjExtractor
from causaganha.decisoes.ner.date import TemporalDateExtractor
from causaganha.decisoes.ner.models import EntityType, JudicialMention
from causaganha.decisoes.ner.money import MonetaryValueExtractor
from causaganha.decisoes.ner.norma import LegalReferenceParser
from causaganha.decisoes.ner.org import OrganizationTrieExtractor
from causaganha.decisoes.structural_segmenter import SectionSpan


class CompositeEntityExtractor:
    """Orquestrador que executa algoritmos específicos para cada natureza de entidade."""

    def __init__(self):
        self.cnj = CnjExtractor()
        self.norma = LegalReferenceParser()
        self.money = MonetaryValueExtractor()
        self.date = TemporalDateExtractor()
        self.org = OrganizationTrieExtractor()

    def extract_from_text(self, text: str, default_section: str = "CORPO") -> list[JudicialMention]:
        """Extrai todas as entidades de um texto genérico sem seções pré-delimitadas."""
        mentions: list[JudicialMention] = []
        mentions.extend(self.cnj.extract(text, default_section))
        mentions.extend(self.norma.extract(text, default_section))
        mentions.extend(self.money.extract(text, default_section))
        mentions.extend(self.date.extract(text, default_section))
        mentions.extend(self.org.extract(text, default_section))
        return sorted(mentions, key=lambda m: m.start)

    def extract_from_sections(self, sections: dict[str, SectionSpan]) -> list[JudicialMention]:
        """Extrai entidades condicionadas pelas seções canônicas de um DocumentStructure.

        Aplica roteamento seccional inteligente para maximizar performance:
        - CNJ: focado no CABECALHO e ENCERRAMENTO.
        - Normas: varre FUNDAMENTACAO, VOTO, DISPOSITIVO e RELATORIO.
        - Valores: varre DISPOSITIVO, HONORARIOS_CUSTAS, CABECALHO e FUNDAMENTACAO.
        - Datas: varre ENCERRAMENTO, CABECALHO e DISPOSITIVO.
        - Organizações: varre todas as seções.
        """
        all_mentions: list[JudicialMention] = []

        for sec_name, span in sections.items():
            sec_type = (
                span.section_type.value
                if hasattr(span.section_type, "value")
                else str(span.section_type)
            )
            text = span.text
            base_offset = span.start

            # 1. CNJ
            if sec_type in {"CABECALHO", "ENCERRAMENTO"}:
                for m in self.cnj.extract(text, sec_type):
                    # Ajusta offset absoluto
                    m.start += base_offset
                    m.end += base_offset
                    all_mentions.append(m)

            # 2. Normas
            if sec_type in {"FUNDAMENTACAO", "VOTO", "DISPOSITIVO", "RELATORIO", "EMENTA"}:
                for m in self.norma.extract(text, sec_type):
                    m.start += base_offset
                    m.end += base_offset
                    all_mentions.append(m)

            # 3. Valores e Custas
            if sec_type in {"DISPOSITIVO", "HONORARIOS_CUSTAS", "CABECALHO", "FUNDAMENTACAO"}:
                for m in self.money.extract(text, sec_type):
                    m.start += base_offset
                    m.end += base_offset
                    all_mentions.append(m)

            # 4. Datas e Prazos
            for m in self.date.extract(text, sec_type):
                m.start += base_offset
                m.end += base_offset
                all_mentions.append(m)

            # 5. Organizações e Grandes Litigantes
            for m in self.org.extract(text, sec_type):
                m.start += base_offset
                m.end += base_offset
                all_mentions.append(m)

        return sorted(all_mentions, key=lambda m: m.start)

    @staticmethod
    def group_by_type(mentions: list[JudicialMention]) -> dict[str, list[dict[str, Any]]]:
        """Gera índice de navegação por tipo de entidade."""
        res: dict[str, list[dict[str, Any]]] = {t.value: [] for t in EntityType}
        for m in mentions:
            res[m.entity_type.value].append(m.to_dict())
        return res

    @staticmethod
    def group_by_section(mentions: list[JudicialMention]) -> dict[str, list[dict[str, Any]]]:
        """Gera índice de navegação por seção do documento."""
        res: dict[str, list[dict[str, Any]]] = {}
        for m in mentions:
            res.setdefault(m.section, []).append(m.to_dict())
        return res

    @staticmethod
    def group_by_role(mentions: list[JudicialMention]) -> dict[str, list[dict[str, Any]]]:
        """Gera índice de navegação por papel processual."""
        res: dict[str, list[dict[str, Any]]] = {}
        for m in mentions:
            res.setdefault(m.role.value, []).append(m.to_dict())
        return res
