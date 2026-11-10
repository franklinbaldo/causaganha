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

    # Primeiro processo é o principal por ausência de metadados explícitos
    m0 = mentions[0]
    assert m0.normalized_value.numero_formatado == "7019913-62.2025.8.22.0007"
    assert m0.normalized_value.is_valid_mod97 is True
    assert m0.role == EntityRole.PROCESSO_PRINCIPAL
    assert m0.confidence == 1.0

    # Segundo processo (mais adiante no texto) é paradigma
    m1 = mentions[1]
    assert m1.role == EntityRole.PROCESSO_PARADIGMA


def test_cnj_main_process_strictly_governed_by_djen_metadata():
    """Garante que o PROCESSO_PRINCIPAL seja governado pelos metadados do DJEN, não pelo cabeçalho."""
    extractor = CnjExtractor()
    # O texto cita no cabeçalho um processo apenso/dependente, e depois o processo real do DJEN
    text = (
        "Distribuição por dependência aos autos nº 7019913-62.2025.8.22.0007. "
        "Trata-se de impugnação autuada sob o nº 7004816-83.2025.8.22.0019."
    )

    # O metadado do DJEN declara que a publicação é dos autos 7004816-83.2025.8.22.0019
    meta_djen = {"numero_processo": "70048168320258220019"}

    mentions = extractor.extract(text, section="CABECALHO", metadata=meta_djen)
    assert len(mentions) == 2

    m_apenso = [m for m in mentions if "7019913" in m.literal][0]
    m_principal = [m for m in mentions if "7004816" in m.literal][0]

    # O primeiro CNJ do cabeçalho NÃO pode ser o principal porque difere do DJEN
    assert m_apenso.role == EntityRole.PROCESSO_CITADO
    assert "distinto do metadado oficial do DJEN" in m_apenso.evidence

    # O processo que coincide com o DJEN é o principal
    assert m_principal.role == EntityRole.PROCESSO_PRINCIPAL
    assert "numero_processo oficial dos metadados do DJEN" in m_principal.evidence


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


def test_composite_injects_djen_process_when_not_in_text():
    """Garante que quando o texto não contém CNJ, o metadado oficial do DJEN é preservado como PROCESSO_PRINCIPAL."""
    composite = CompositeEntityExtractor()
    sections = {
        "cabecalho": SectionSpan(
            section_type=SectionType.CABECALHO,
            start=0,
            end=60,
            text="PODER JUDICIÁRIO. 1ª VARA CÍVEL. Ação de Cobrança.",
            confidence=0.95,
        ),
        "dispositivo": SectionSpan(
            section_type=SectionType.DISPOSITIVO,
            start=61,
            end=140,
            text="Julgo procedente o pedido para condenar o réu em R$ 1.000,00.",
            confidence=0.92,
        ),
    }

    meta = {"numero_processo": "70199136220258220007"}
    mentions = composite.extract_from_sections(sections, metadata=meta)

    # O PROCESSO_PRINCIPAL deve existir via metadados do DJEN
    cnjs = [m for m in mentions if m.entity_type == EntityType.CNJ]
    assert len(cnjs) == 1
    assert cnjs[0].role == EntityRole.PROCESSO_PRINCIPAL
    assert cnjs[0].section == "METADADOS_DJEN"
    assert cnjs[0].normalized_value.numero_formatado == "7019913-62.2025.8.22.0007"
    assert "Metadados do DJEN" in cnjs[0].evidence


def test_person_advogado_grounded_by_djen_metadata():
    """Garante que partes, advogados e OABs sejam identificados e vinculados com autoridade aos metadados do DJEN."""
    from causaganha.decisoes.ner.person_advogado import PersonAdvogadoExtractor

    extractor = PersonAdvogadoExtractor()
    text = (
        "Requerente: Carlos Eduardo Santos. "
        "Advogada: Dra. Patricia Lima, OAB/RO 12345. "
        "Requerido: Banco Santander Brasil S/A. "
        "Juiz de Direito: Dr. Wilson Martins."
    )

    meta_djen = {
        "polo_ativo": "Carlos Eduardo Santos",
        "polo_passivo": "Banco Santander Brasil S/A",
        "advogado": "Patricia Lima",
        "oab": "12345",
        "uf_oab": "RO",
        "judge_name": "Wilson Martins",
    }

    mentions = extractor.extract(text, section="CABECALHO", metadata=meta_djen)

    # 1. Polo Ativo (autor) confirmado pelo DJEN
    m_autor = [m for m in mentions if m.role == EntityRole.POLO_ATIVO][0]
    assert m_autor.literal == "Carlos Eduardo Santos"
    assert m_autor.confidence == 1.0
    assert "polo ativo confirmado pelos metadados oficiais do djen" in m_autor.evidence.lower()

    # 2. OAB confirmada pelo DJEN
    m_oab = [m for m in mentions if m.entity_type == EntityType.OAB][0]
    assert m_oab.normalized_value.numero == "12345"
    assert m_oab.normalized_value.uf == "RO"
    assert m_oab.confidence == 1.0

    # 3. Advogada confirmada pelo DJEN
    m_adv = [
        m for m in mentions if m.entity_type == EntityType.PESSOA and m.role == EntityRole.ADVOGADO
    ][0]
    assert "Patricia Lima" in m_adv.literal
    assert m_adv.confidence == 1.0

    # 4. Magistrado confirmado pelo DJEN
    m_juiz = [m for m in mentions if m.role == EntityRole.MAGISTRADO][0]
    assert "Wilson Martins" in m_juiz.literal
    assert m_juiz.confidence == 1.0


def test_composite_injects_djen_parties_when_omitted_in_text():
    """Garante que as partes oficiais do DJEN sejam preservadas no grafo mesmo se o texto omitir seus nomes."""
    composite = CompositeEntityExtractor()
    sections = {
        "cabecalho": SectionSpan(
            section_type=SectionType.CABECALHO,
            start=0,
            end=60,
            text="PODER JUDICIÁRIO. Processo de Execução.",
            confidence=0.95,
        ),
        "dispositivo": SectionSpan(
            section_type=SectionType.DISPOSITIVO,
            start=61,
            end=140,
            text="Defiro a penhora online via Sisbajud.",
            confidence=0.92,
        ),
    }

    meta = {
        "numero_processo": "70199136220258220007",
        "polo_ativo": "Empresa Alfa Ltda",
        "polo_passivo": "Devedor Beta",
    }
    mentions = composite.extract_from_sections(sections, metadata=meta)

    # Verifica que polo ativo e polo passivo foram injetados com autoridade a partir dos metadados do DJEN
    autor = [m for m in mentions if m.role == EntityRole.POLO_ATIVO][0]
    assert autor.literal == "Empresa Alfa Ltda"
    assert autor.section == "METADADOS_DJEN"
    assert "Fonte Primária Oficial" in autor.evidence

    reu = [m for m in mentions if m.role == EntityRole.POLO_PASSIVO][0]
    assert reu.literal == "Devedor Beta"
    assert reu.section == "METADADOS_DJEN"
    assert "Fonte Primária Oficial" in reu.evidence


def test_entities_extracted_across_all_sections():
    """Garante que entidades (valores, normas, CNJs, pessoas) sejam reconhecidas em todas as seções."""
    composite = CompositeEntityExtractor()
    sections = {
        "relatorio": SectionSpan(
            section_type=SectionType.RELATORIO,
            start=0,
            end=120,
            text="O autor pugnou por danos morais de R$ 50.000,00 nos autos do processo 7019913-62.2025.8.22.0007.",
            confidence=0.90,
        ),
        "honorarios_custas": SectionSpan(
            section_type=SectionType.HONORARIOS_CUSTAS,
            start=121,
            end=220,
            text="Condeno o réu em honorários nos termos do art. 85, § 2º, do CPC no valor de R$ 3.000,00.",
            confidence=0.95,
        ),
    }

    mentions = composite.extract_from_sections(sections)

    # 1. Valor em R$ no Relatório deve ser extraído (antes era filtrado!)
    valores_relatorio = [
        m for m in mentions if m.entity_type == EntityType.VALOR and m.section == "RELATORIO"
    ]
    assert len(valores_relatorio) >= 1
    assert "50.000,00" in valores_relatorio[0].literal

    # 2. Norma jurídica em Honorários deve ser extraída (antes era filtrada!)
    normas_honorarios = [
        m
        for m in mentions
        if m.entity_type == EntityType.NORMA and m.section == "HONORARIOS_CUSTAS"
    ]
    assert len(normas_honorarios) >= 1
    assert "art. 85" in normas_honorarios[0].literal.lower()

    # 3. CNJ citado no Relatório deve ser extraído
    cnjs_relatorio = [
        m for m in mentions if m.entity_type == EntityType.CNJ and m.section == "RELATORIO"
    ]
    assert len(cnjs_relatorio) >= 1
    assert "7019913" in cnjs_relatorio[0].literal
