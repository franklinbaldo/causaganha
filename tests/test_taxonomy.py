"""Testes unitários para o DocumentTaxonomyRegistry e taxonomia especializada."""

import pytest
from causaganha.decisoes.taxonomy import (
    DocumentTaxonomyRegistry,
    MacroCategory,
    TaxonomyClassification,
)


@pytest.fixture
def registry():
    return DocumentTaxonomyRegistry()


def test_classify_edital_citacao(registry):
    text = (
        "EDITAL DE CITAÇÃO PRAZO: 15 DIAS. Processo n. 7019913-62.2025.8.22.0007. "
        "RÉU: R. M. F., atualmente em local incerto e não sabido. "
        "FINALIDADE: Citar o acusado para responder à acusação."
    )
    res = registry.classify(text, metadata={"doc_type": "outro"})
    assert res.macro_category == MacroCategory.EDITAL
    assert res.specific_category == "EDITAL_CITACAO"
    assert "citacao" in res.tags
    assert "prazo_15d" in res.tags
    assert res.confidence >= 0.95


def test_classify_edital_leilao(registry):
    text = (
        "EDITAL DE LEILÃO E PRAÇA PÚBLICA DE ALIENAÇÃO JUDICIAL. "
        "Faz saber que levará a público leilão de bens penhorados no processo de execução."
    )
    res = registry.classify(text)
    assert res.macro_category == MacroCategory.EDITAL
    assert res.specific_category == "EDITAL_LEILAO_PRACA"
    assert "leilao" in res.tags


def test_classify_intimacao_audiencia(registry):
    text = (
        "Processo nº : 7004816-83.2025.8.22.0019. Intimação por Diário de Justiça. "
        "Audiência de Conciliação. Ficam as partes intimadas acerca da Audiência de Conciliação "
        "deste processo a ser realizada em 03/03/2026."
    )
    res = registry.classify(text, metadata={"doc_type": "outro"})
    assert res.macro_category == MacroCategory.PUBLICACAO_COMUNICACAO
    assert res.specific_category == "INTIMACAO_AUDIENCIA"
    assert "audiencia" in res.tags
    assert "pauta" in res.tags


def test_classify_intimacao_cumprimento_sentenca(registry):
    text = (
        "Fica o executado intimado, na pessoa de seu advogado, para efetuar o pagamento voluntário "
        "do débito no prazo de 15 dias, sob pena de multa de 10% nos termos do art. 523 do CPC."
    )
    res = registry.classify(text)
    assert res.macro_category == MacroCategory.PUBLICACAO_COMUNICACAO
    assert res.specific_category == "INTIMACAO_PAGAMENTO_CUMPRIMENTO"
    assert "art_523_cpc" in res.tags


def test_classify_acordao_apelacao(registry):
    text = (
        "TRIBUNAL DE JUSTIÇA. Apelação Cível nº 0012345-67.2024.8.22.0001. "
        "ACÓRDÃO: Vistos, relatados e discutidos estes autos, acordam os Desembargadores em "
        "dar provimento ao recurso de apelação."
    )
    res = registry.classify(
        text, metadata={"procedural_class": "apelação", "relator": "Des. Silva"}
    )
    assert res.macro_category == MacroCategory.ACORDAO
    assert res.specific_category == "ACORDAO_APELACAO"
    assert "segundo_grau" in res.tags
    assert res.cnj_class_hint == "198"


def test_classify_tutela_urgencia_interlocutoria(registry):
    text = (
        "DECISÃO INTERLOCUTÓRIA. Trata-se de pedido de tutela de urgência inaudita altera parte "
        "para determinar o fornecimento imediato de medicamento, sob pena de multa diária."
    )
    res = registry.classify(text, metadata={"doc_type": "decisão interlocutória"})
    assert res.macro_category == MacroCategory.DECISAO_INTERLOCUTORIA
    assert res.specific_category == "DECISAO_TUTELA_URGENCIA_LIMINAR"
    assert "liminar" in res.tags


def test_classify_medida_protetiva_maria_da_penha(registry):
    text = (
        "Classe: Medidas Protetivas de Urgência (Lei Maria da Penha) - Criminal. "
        "DECISÃO: Vistos. Defiro as medidas cautelares proibindo aproximação da ofendida."
    )
    res = registry.classify(text, metadata={"procedural_class": "Medidas Protetivas"})
    assert res.macro_category == MacroCategory.DECISAO_INTERLOCUTORIA
    assert res.specific_category == "DECISAO_MEDIDA_PROTETIVA_CAUTELAR"
    assert "penal" in res.tags


def test_classify_sentenca_homologatoria(registry):
    text = (
        "SENTENÇA. As partes compuseram seus interesses e protocolaram termo conjunto. "
        "Ante o exposto, HOMOLOGO O ACORDO entabulado entre as partes e extingo o processo com resolução do mérito."
    )
    res = registry.classify(text, metadata={"doc_type": "sentença"})
    assert res.macro_category == MacroCategory.SENTENCA
    assert res.specific_category == "SENTENCA_HOMOLOGATORIA_ACORDO"
    assert "autocomposicao" in res.tags


def test_classify_certidao_transito_julgado(registry):
    text = (
        "PODER JUDICIÁRIO. CERTIDÃO DE TRÂNSITO EM JULGADO. "
        "Certifico e dou fé que a r. sentença de fls. transitou em julgado em 10/02/2026."
    )
    res = registry.classify(text)
    assert res.macro_category == MacroCategory.ATO_CARTORARIO
    assert res.specific_category == "CERTIDAO_TRANSITO_JULGADO"
    assert "coisa_julgada" in res.tags


def test_dynamic_registry_extensibility(registry):
    """Verifica que novos tipos podem ser registrados em tempo de execução sem alterar código-fonte."""
    # Registra uma nova categoria customizada (ex: Notificação de Falência / Recuperação Judicial)
    registry.register_rule(
        name="falencia_specialized",
        priority=110,  # Alta prioridade
        matcher=lambda text, meta: "recuperacao judicial" in text and "edital de credores" in text,
        classifier=lambda text, meta: TaxonomyClassification(
            macro_category=MacroCategory.EDITAL,
            specific_category="EDITAL_QUADRO_GERAL_CREDORES",
            tags=["empresarial", "recuperacao_judicial", "art_52_lei_11101"],
            confidence=0.99,
        ),
    )

    sample_doc = "EDITAL DE CREDORES nos autos da Recuperação Judicial da empresa XYZ S/A, para conferência de créditos."
    res = registry.classify(sample_doc)
    assert res.specific_category == "EDITAL_QUADRO_GERAL_CREDORES"
    assert res.rule_matched == "falencia_specialized"
    assert "art_52_lei_11101" in res.tags


def test_conflict_sentenca_mentioning_edital(registry):
    """Garante que 'doc_type=sentença' não vire EDITAL por mera menção no corpo."""
    text = "SENTENÇA. O réu foi citado por edital de citação. Julgo procedente o pedido."
    res = registry.classify(text, metadata={"doc_type": "sentença"})
    assert res.macro_category == MacroCategory.SENTENCA
    assert res.specific_category == "SENTENCA_PROCEDENCIA"
    assert "contem_mencao_edital" in res.tags


def test_conflict_sentenca_mentioning_intimacao(registry):
    """Garante que sentença intimando partes ao final não vire PUBLICACAO_COMUNICACAO."""
    text = "SENTENÇA. Analisados os autos. Julgo improcedente a ação. Ficam as partes intimadas para recorrer."
    res = registry.classify(text, metadata={"doc_type": "sentença"})
    assert res.macro_category == MacroCategory.SENTENCA
    assert res.specific_category == "SENTENCA_IMPROCEDENCIA"
    assert "contem_intimacao_partes" in res.tags


def test_conflict_monocratica_with_relator(registry):
    """Garante que 'doc_type=decisão monocrática' com relator vire DECISAO_MONOCRATICA e não ACORDAO."""
    text = "DECISÃO MONOCRÁTICA. Trata-se de recurso especial. Nego seguimento ao recurso, com base no art. 932 do CPC."
    res = registry.classify(
        text, metadata={"doc_type": "decisão monocrática", "relator": "Ministro Fulano"}
    )
    assert res.macro_category == MacroCategory.DECISAO_MONOCRATICA
    assert res.specific_category == "DECISAO_MONOCRATICA_RELATOR"
    assert "decisao_unipessoal" in res.tags
