"""Parser e Normalizador Temporal de Datas e Prazos Processuais."""

from __future__ import annotations

import re

from causaganha.decisoes.ner.models import DateValue, EntityRole, EntityType, JudicialMention

MONTHS_MAP = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

# Regex para datas numéricas: DD/MM/AAAA
REGEX_NUMERIC_DATE = re.compile(
    r"\b(?P<day>0?[1-9]|[12][0-9]|3[01])/(?P<month>0?[1-9]|1[0-2])/(?P<year>20[12]\d)\b"
)

# Regex para datas por extenso: 10 de novembro de 2026
REGEX_TEXT_DATE = re.compile(
    r"\b(?P<day>0?[1-9]|[12][0-9]|3[01])\s+de\s+(?P<month>[a-zA-Zç]+)\s+de\s+(?P<year>20[12]\d)\b",
    re.IGNORECASE,
)

# Regex para prazos processuais: prazo de 15 dias (úteis)
REGEX_DEADLINE = re.compile(
    r"\bprazo\s+(?:legal\s+)?de\s+(?P<days>\d{1,3})\s+(?:\([^\)]+\)\s+)?dias(?:\s+[uú]teis)?\b",
    re.IGNORECASE,
)


class TemporalDateExtractor:
    """Extrator especializado em datas civis e prazos do Código de Processo Civil."""

    def extract(self, text: str, section: str = "ENCERRAMENTO") -> list[JudicialMention]:
        mentions: list[JudicialMention] = []

        # 1. Datas Numéricas (DD/MM/AAAA)
        for m in REGEX_NUMERIC_DATE.finditer(text):
            day = int(m.group("day"))
            month = int(m.group("month"))
            year = int(m.group("year"))
            iso_str = f"{year:04d}-{month:02d}-{day:02d}"

            role = (
                EntityRole.DATA_JULGAMENTO
                if section == "ENCERRAMENTO"
                else EntityRole.DATA_GENERICA
            )
            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.DATA,
                    normalized_value=DateValue(
                        iso_date=iso_str,
                        year=year,
                        month=month,
                        day=day,
                        is_deadline=False,
                        raw_text=m.group(0),
                    ),
                    role=role,
                    confidence=0.99,
                    evidence=f"Data numérica identificada em {section}",
                )
            )

        # 2. Datas por Extenso (DD de mês de AAAA)
        for m in REGEX_TEXT_DATE.finditer(text):
            month_name = m.group("month").lower()
            if month_name not in MONTHS_MAP:
                continue
            day = int(m.group("day"))
            month = MONTHS_MAP[month_name]
            year = int(m.group("year"))
            iso_str = f"{year:04d}-{month:02d}-{day:02d}"

            role = (
                EntityRole.DATA_JULGAMENTO
                if section == "ENCERRAMENTO"
                else EntityRole.DATA_GENERICA
            )
            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.DATA,
                    normalized_value=DateValue(
                        iso_date=iso_str,
                        year=year,
                        month=month,
                        day=day,
                        is_deadline=False,
                        raw_text=m.group(0),
                    ),
                    role=role,
                    confidence=0.99,
                    evidence=f"Data por extenso identificada em {section}",
                )
            )

        # 3. Prazos Processuais
        for m in REGEX_DEADLINE.finditer(text):
            days = int(m.group("days"))
            mentions.append(
                JudicialMention(
                    literal=m.group(0),
                    start=m.start(),
                    end=m.end(),
                    section=section,
                    entity_type=EntityType.DATA,
                    normalized_value=DateValue(
                        iso_date=None,
                        year=None,
                        month=None,
                        day=None,
                        is_deadline=True,
                        deadline_days=days,
                        raw_text=m.group(0),
                    ),
                    role=EntityRole.PRAZO_MANIFESTACAO,
                    confidence=0.97,
                    evidence="Cominação expressa de prazo processual",
                )
            )

        return mentions
