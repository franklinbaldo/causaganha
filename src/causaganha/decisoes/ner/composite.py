"""Orquestrador Composto de Entidades Judiciais Especializadas (Multi-Algorithm NER)."""

from __future__ import annotations

from typing import Any

from causaganha.decisoes.ner.cnj import CnjExtractor
from causaganha.decisoes.ner.date import TemporalDateExtractor
from causaganha.decisoes.ner.models import (
    CnjValue,
    EntityRole,
    EntityType,
    JudicialMention,
    PersonValue,
)
from causaganha.decisoes.ner.money import MonetaryValueExtractor
from causaganha.decisoes.ner.norma import LegalReferenceParser
from causaganha.decisoes.ner.org import OrganizationTrieExtractor
from causaganha.decisoes.ner.person_advogado import PersonAdvogadoExtractor
from causaganha.decisoes.structural_segmenter import SectionSpan
from causaganha.processos.cnj import formatar_cnj, normalizar_cnj, validar_digito_verificador


class CompositeEntityExtractor:
    """Orquestrador que executa algoritmos específicos para cada natureza de entidade."""

    def __init__(self):
        self.cnj = CnjExtractor()
        self.norma = LegalReferenceParser()
        self.money = MonetaryValueExtractor()
        self.date = TemporalDateExtractor()
        self.org = OrganizationTrieExtractor()
        self.person = PersonAdvogadoExtractor()

    def extract_from_text(
        self,
        text: str,
        default_section: str = "CORPO",
        metadata: dict[str, Any] | None = None,
    ) -> list[JudicialMention]:
        """Extrai todas as entidades de um texto genérico sem seções pré-delimitadas."""
        meta = metadata or {}
        mentions: list[JudicialMention] = []
        mentions.extend(self.cnj.extract(text, default_section, metadata=meta))
        mentions.extend(self.norma.extract(text, default_section))
        mentions.extend(self.money.extract(text, default_section))
        mentions.extend(self.date.extract(text, default_section))
        mentions.extend(self.org.extract(text, default_section))
        mentions.extend(self.person.extract(text, default_section, metadata=meta))
        return self._inject_sovereign_metadata(mentions, meta)

    def _inject_sovereign_metadata(
        self,
        mentions: list[JudicialMention],
        meta: dict[str, Any],
    ) -> list[JudicialMention]:
        djen_raw = (
            meta.get("numero_processo")
            or meta.get("numeroprocessocommascara")
            or meta.get("numero_processo_mascara")
            or meta.get("cnj")
            or meta.get("process_number")
        )
        djen_clean = normalizar_cnj(str(djen_raw)) if djen_raw else ""

        has_main = any(m.role == EntityRole.PROCESSO_PRINCIPAL for m in mentions)
        if not has_main and djen_clean and len(djen_clean) == 20:
            formatted_djen = formatar_cnj(djen_clean)
            mentions.insert(
                0,
                JudicialMention(
                    literal=formatted_djen,
                    start=0,
                    end=0,
                    section="METADADOS_DJEN",
                    entity_type=EntityType.CNJ,
                    normalized_value=CnjValue(
                        numero_formatado=formatted_djen,
                        sequencial=djen_clean[:7],
                        digito_verificador=djen_clean[7:9],
                        ano=int(djen_clean[9:13]),
                        ramo_justica=int(djen_clean[13:14]),
                        tribunal=int(djen_clean[14:16]),
                        origem=djen_clean[16:20],
                        is_valid_mod97=validar_digito_verificador(djen_clean),
                    ),
                    role=EntityRole.PROCESSO_PRINCIPAL,
                    confidence=1.0,
                    evidence="Fonte Primária Oficial: Metadados do DJEN",
                ),
            )

        autor_djen = meta.get("polo_ativo") or meta.get("autor")
        if autor_djen and not any(m.role == EntityRole.POLO_ATIVO for m in mentions):
            mentions.append(
                JudicialMention(
                    literal=str(autor_djen),
                    start=0,
                    end=0,
                    section="METADADOS_DJEN",
                    entity_type=EntityType.PESSOA,
                    normalized_value=PersonValue(nome=str(autor_djen), polo="ATIVO"),
                    role=EntityRole.POLO_ATIVO,
                    confidence=1.0,
                    evidence="Fonte Primária Oficial: Polo Ativo do DJEN",
                )
            )

        reu_djen = meta.get("polo_passivo") or meta.get("reu")
        if reu_djen and not any(m.role == EntityRole.POLO_PASSIVO for m in mentions):
            mentions.append(
                JudicialMention(
                    literal=str(reu_djen),
                    start=0,
                    end=0,
                    section="METADADOS_DJEN",
                    entity_type=EntityType.PESSOA,
                    normalized_value=PersonValue(nome=str(reu_djen), polo="PASSIVO"),
                    role=EntityRole.POLO_PASSIVO,
                    confidence=1.0,
                    evidence="Fonte Primária Oficial: Polo Passivo do DJEN",
                )
            )

        return sorted(mentions, key=lambda m: m.start)

    def extract_from_sections(
        self,
        sections: dict[str, SectionSpan],
        metadata: dict[str, Any] | None = None,
    ) -> list[JudicialMention]:
        """Extrai entidades condicionadas pelas seções canônicas de um DocumentStructure.

        Aplica roteamento seccional inteligente para maximizar performance:
        - CNJ: focado no CABECALHO e ENCERRAMENTO (com validação pelo metadado oficial do DJEN).
        - Normas: varre FUNDAMENTACAO, VOTO, DISPOSITIVO e RELATORIO.
        - Valores: varre DISPOSITIVO, HONORARIOS_CUSTAS, CABECALHO e FUNDAMENTACAO.
        - Datas: varre ENCERRAMENTO, CABECALHO e DISPOSITIVO.
        - Organizações: varre todas as seções.
        - Pessoas, Advogados e OABs: varre CABECALHO, RELATORIO, DISPOSITIVO e ENCERRAMENTO com vinculação ao DJEN.
        """
        meta = metadata or {}
        all_mentions: list[JudicialMention] = []

        for sec_name, span in sections.items():
            sec_type = (
                span.section_type.value
                if hasattr(span.section_type, "value")
                else str(span.section_type)
            )
            text = span.text
            base_offset = span.start

            # 1. CNJ (Validado matematicamente por Módulo 97 e ancorado no DJEN)
            for m in self.cnj.extract(text, sec_type, metadata=meta):
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

            # 6. Pessoas, Advogados e OABs (Vinculados aos metadados do DJEN)
            if sec_type in {"CABECALHO", "RELATORIO", "FUNDAMENTACAO", "DISPOSITIVO", "ENCERRAMENTO"}:
                for m in self.person.extract(text, sec_type, metadata=meta):
                    m.start += base_offset
                    m.end += base_offset
                    all_mentions.append(m)

        return self._inject_sovereign_metadata(all_mentions, meta)

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
