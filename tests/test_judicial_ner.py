"""Testes unitários para o Reconhecimento de Entidades e Papéis Jurídicos (Judicial NER)."""

from causaganha.decisoes.ner import (
    CnjExtractor,
    CompositeEntityExtractor,
    EntityRole,
    EntityType,
    LegalReferenceParser,
    MonetaryValueExtractor,
    OrganizationTrieExtractor,
    TemporalDateExtractor,
    validate_cnj_modulo_97,
)
from causaganha.decisoes.structural_segmenter import SectionSpan, SectionType


def test_validate_cnj_modulo_97():
    # Processo real válido do TJRO
    assert (
        validate_cnj_modulo_97(
            seq="7019913",
            dv="62",
            ano="2025",
            ramo="8",
            trib="22",
            origem="0007",
        )
        is True
    )

    # Processo com dígito adulterado / corrompido
    assert (
        validate_cnj_modulo_97(
            seq="7019913",
            dv="99",
            ano="2025",
            ramo="8",
            trib="22",
            origem="0007",
        )
        is False
    )


def test_cnj_extractor_detection_and_roles():
    extractor = CnjExtractor()
    text = (
        "Processo nº 7019913-62.2025.8.22.0007. "
        "Ação de Cobrança em trâmite na 1ª Vara Cível. "
        "Conforme decidido no processo paradigma nº 0001234-56.2024.8.22.0001, indefiro o pedido."
    )

    mentions = extractor.extract(text, section="CABECALHO")
    assert len(mentions) >= 2

    # Primeiro processo é o principal
    m0 = mentions[0]
    assert m0.normalized_value.numero_formatado == "7019913-62.2025.8.22.0007"
    assert m0.normalized_value.is_valid_mod97 is True
    assert m0.role == EntityRole.PROCESSO_PRINCIPAL
    assert m0.confidence == 1.0

    # Segundo processo (mais adiante no texto) é paradigma
    m1 = mentions[1]
    assert m1.role == EntityRole.PROCESSO_PARADIGMA


def test_legal_reference_parser_hierarchy_and_context():
    parser = LegalReferenceParser()
    text = (
        "Trata-se de ação sob o rito do Código de Processo Civil. "
        "O autor fundamenta seu pedido no art. 186 e art. 927. "
        "Ante o exposto, extingo o processo com resolução do mérito nos termos do art. 485, § 1º, inc. VI, do CPC."
    )

    mentions = parser.extract(text, section="DISPOSITIVO")
    assert len(mentions) >= 3

    # Dispositivo legal com diploma explícito
    disp_m = [m for m in mentions if "485" in m.literal][0]
    ref = disp_m.normalized_value
    assert ref.diploma == "CPC"
    assert ref.artigo == "485"
    assert "1" in ref.paragrafo
    assert ref.inciso == "VI"
    assert disp_m.role == EntityRole.DISPOSITIVO_LEGAL_APLICADO

    # Norma com anáfora resolvida pelo contexto do CPC
    art_186 = [m for m in mentions if "186" in m.literal][0]
    assert art_186.normalized_value.diploma == "CPC"


def test_money_extractor_roles_and_percentages():
    extractor = MonetaryValueExtractor()
    text = (
        "Valor da causa fixado em R$ 50.000,00.\n"
        "Condeno o réu ao pagamento de R$ 8.500,00 a título de indenização por danos morais.\n"
        "Fixo multa diária no valor de R$ 500,00 para o caso de descumprimento.\n"
        "Condeno ainda ao pagamento de custas e honorários advocatícios arbitrados em 10% sobre o valor da condenação."
    )

    mentions = extractor.extract(text, section="DISPOSITIVO")
    assert len(mentions) == 4

    # 1. Valor da causa
    m_causa = [m for m in mentions if m.normalized_value.amount == 50000.0][0]
    assert m_causa.role == EntityRole.VALOR_DA_CAUSA

    # 2. Condenação de mérito
    m_cond = [m for m in mentions if m.normalized_value.amount == 8500.0][0]
    assert m_cond.role == EntityRole.VALOR_CONDENACAO_PRINCIPAL
    assert m_cond.normalized_value.currency == "BRL"

    # 3. Multa / Astreintes
    m_multa = [m for m in mentions if m.normalized_value.amount == 500.0][0]
    assert m_multa.role == EntityRole.VALOR_ASTREINTES_MULTA

    # 4. Percentual de honorários
    m_pct = [m for m in mentions if m.normalized_value.is_percentage][0]
    assert m_pct.normalized_value.amount == 10.0
    assert m_pct.role == EntityRole.PERCENTUAL_SUCUMBENCIA


def test_date_extractor_numeric_and_deadlines():
    extractor = TemporalDateExtractor()
    text = (
        "Audiência designada para 15/05/2025. "
        "Intime-se a parte ré para apresentar contestação no prazo de 15 dias úteis. "
        "Porto Velho, 10 de novembro de 2026."
    )

    mentions = extractor.extract(text, section="ENCERRAMENTO")
    assert len(mentions) == 3

    # Data numérica
    m_num = [m for m in mentions if "15/05/2025" in m.literal][0]
    assert m_num.normalized_value.iso_date == "2025-05-15"

    # Prazo
    m_prazo = [m for m in mentions if m.normalized_value.is_deadline][0]
    assert m_prazo.normalized_value.deadline_days == 15
    assert m_prazo.role == EntityRole.PRAZO_MANIFESTACAO

    # Data por extenso
    m_ext = [m for m in mentions if "novembro" in m.literal][0]
    assert m_ext.normalized_value.iso_date == "2026-11-10"
    assert m_ext.role == EntityRole.DATA_JULGAMENTO


def test_org_extractor_litigants():
    extractor = OrganizationTrieExtractor()
    text = (
        "Requerente: Maria da Silva. "
        "Requeridos: Banco do Brasil S/A e Energisa Rondônia Distribuidora. "
        "Oficie-se ao INSS para prestar informações."
    )

    mentions = extractor.extract(text, section="CABECALHO")
    assert len(mentions) == 3

    names = {m.normalized_value["canonical_name"] for m in mentions}
    assert "BANCO_DO_BRASIL_SA" in names
    assert "ENERGISA_DISTRIBUIDORA" in names
    assert "INSS_INSTITUTO_NACIONAL_SEGURO_SOCIAL" in names


def test_composite_extractor_with_sections():
    composite = CompositeEntityExtractor()
    sections = {
        "cabecalho": SectionSpan(
            section_type=SectionType.CABECALHO,
            start=0,
            end=120,
            text="PODER JUDICIÁRIO. Processo nº 7019913-62.2025.8.22.0007. Autor: João. Réu: Energisa Rondônia. Valor da causa: R$ 10.000,00.",
            confidence=0.95,
        ),
        "dispositivo": SectionSpan(
            section_type=SectionType.DISPOSITIVO,
            start=121,
            end=280,
            text="Ante o exposto, julgo procedente o pedido nos termos do art. 487, I, do CPC, para condenar o réu ao pagamento de R$ 5.000,00. P.R.I.",
            confidence=0.92,
        ),
        "encerramento": SectionSpan(
            section_type=SectionType.ENCERRAMENTO,
            start=281,
            end=340,
            text="Porto Velho, 10 de novembro de 2026. Juiz de Direito.",
            confidence=0.90,
        ),
    }

    mentions = composite.extract_from_sections(sections)
    assert len(mentions) >= 5

    by_type = composite.group_by_type(mentions)
    assert len(by_type[EntityType.CNJ.value]) == 1
    assert len(by_type[EntityType.ORGANIZACAO.value]) == 1
    assert len(by_type[EntityType.VALOR.value]) == 2
    assert len(by_type[EntityType.NORMA.value]) == 1
    assert len(by_type[EntityType.DATA.value]) == 1

    by_sec = composite.group_by_section(mentions)
    assert "CABECALHO" in by_sec
    assert "DISPOSITIVO" in by_sec
    assert "ENCERRAMENTO" in by_sec
