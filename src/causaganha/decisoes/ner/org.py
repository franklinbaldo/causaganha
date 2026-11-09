"""Extrator de Grandes Litigantes e Organizações Jurídicas em Tempo Linear."""

from __future__ import annotations

import re

from causaganha.decisoes.ner.models import EntityRole, EntityType, JudicialMention

# Catálogo canônico dos maiores litigantes do Judiciário Brasileiro (CNJ Raio-X dos Litigantes)
ORGANIZATIONS_CATALOG = [
    # Instituições Financeiras
    (
        r"\b(?:banco\s+do\s+brasil(?:\s+s/?a)?|bb)\b",
        "BANCO_DO_BRASIL_SA",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (
        r"\b(?:caixa\s+econ[oô]mica\s+federal|cef)\b",
        "CAIXA_ECONOMICA_FEDERAL",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (
        r"\b(?:banco\s+bradesco(?:\s+s/?a)?|bradesco)\b",
        "BANCO_BRADESCO_SA",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (
        r"\b(?:ita[uú]\s+unibanco(?:\s+s/?a)?|banco\s+ita[uú]|ita[uú])\b",
        "ITAU_UNIBANCO_SA",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (
        r"\b(?:banco\s+santander(?:\s+\(brasil\)\s+s/?a)?|santander)\b",
        "BANCO_SANTANDER_BRASIL_SA",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (
        r"\b(?:banco\s+pan(?:\s+s/?a)?|panamericano)\b",
        "BANCO_PAN_SA",
        EntityRole.INSTITUICAO_FINANCEIRA,
    ),
    (r"\b(?:banco\s+bmg(?:\s+s/?a)?|bmg)\b", "BANCO_BMG_SA", EntityRole.INSTITUICAO_FINANCEIRA),
    # Concessionárias de Serviços Públicos (Energia, Água, Gás)
    (
        r"\b(?:energisa(?:\s+rond[oô]nia|\s+distribuidora)?)\b",
        "ENERGISA_DISTRIBUIDORA",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    (r"\b(?:enel(?:\s+distribui[cç][aã]o)?)\b", "ENEL_BRASIL", EntityRole.EMPRESA_SERVICO_PUBLICO),
    (
        r"\b(?:equatorial\s+energia|equatorial)\b",
        "EQUATORIAL_ENERGIA",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    (
        r"\b(?:caerd|companhia\s+de\s+[aá]guas\s+e\s+esgotos\s+de\s+rond[oô]nia)\b",
        "CAERD_RO",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    # Telecomunicações
    (
        r"\b(?:claro(?:\s+s/?a|\s+telecom)?|embratel)\b",
        "CLARO_SA",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    (
        r"\b(?:tim(?:\s+s/?a|\s+celular)?)\b",
        "TIM_SA",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    (
        r"\b(?:telef[oô]nica\s+brasil|telef[oô]nica|vivo)\b",
        "TELEFONICA_BRASIL_VIVO",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    (
        r"\b(?:oi\s+s/?a(?:\s+-\s+em\s+recupera[cç][aã]o\s+judicial)?|telemar)\b",
        "OI_SA",
        EntityRole.EMPRESA_SERVICO_PUBLICO,
    ),
    # Órgãos Públicos e Seguridade Social
    (
        r"\b(?:inss|instituto\s+nacional\s+do\s+seguro\s+social)\b",
        "INSS_INSTITUTO_NACIONAL_SEGURO_SOCIAL",
        EntityRole.ORGAO_PUBLICO,
    ),
    (
        r"\b(?:uni[aã]o\s+federal|fazenda\s+nacional)\b",
        "UNIAO_FEDERAL",
        EntityRole.ORGAO_PUBLICO,
    ),
    (
        r"\b(?:estado\s+de\s+rond[oô]nia|fazenda\s+p[uú]blica\s+do\s+estado\s+de\s+rond[oô]nia)\b",
        "ESTADO_DE_RONDONIA",
        EntityRole.ORGAO_PUBLICO,
    ),
    (
        r"\b(?:minist[eé]rio\s+p[uú]blico(?:\s+do\s+estado|\s+federal)?|mpro|mpf)\b",
        "MINISTERIO_PUBLICO",
        EntityRole.ORGAO_PUBLICO,
    ),
    (
        r"\b(?:defensoria\s+p[uú]blica(?:\s+do\s+estado|\s+da\s+uni[aã]o)?|dpe-ro|dpu)\b",
        "DEFENSORIA_PUBLICA",
        EntityRole.ORGAO_PUBLICO,
    ),
]

COMPILED_ORGS = [
    (re.compile(pattern, re.IGNORECASE), canonical, role)
    for pattern, canonical, role in ORGANIZATIONS_CATALOG
]


class OrganizationTrieExtractor:
    """Extrator em tempo linear para os maiores litigantes e entidades do sistema de justiça."""

    def extract(self, text: str, section: str = "CABECALHO") -> list[JudicialMention]:
        mentions: list[JudicialMention] = []

        for regex, canonical, default_role in COMPILED_ORGS:
            for m in regex.finditer(text):
                role = default_role
                mentions.append(
                    JudicialMention(
                        literal=m.group(0),
                        start=m.start(),
                        end=m.end(),
                        section=section,
                        entity_type=EntityType.ORGANIZACAO,
                        normalized_value={"canonical_name": canonical, "catalog_role": role.value},
                        role=role,
                        confidence=0.99,
                        evidence=f"Grande litigante do catálogo CNJ identificado em {section}",
                    )
                )

        return mentions
