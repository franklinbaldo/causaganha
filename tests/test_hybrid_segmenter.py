"""Testes unitários para o Segmentador Híbrido de Dispositivo Judicial.

Valida:
- Divisão de unidades estruturais (multiline vs flat text OCR/DJEN)
- Extração de features com metadados DJEN
- Extração automática de cabeçalho
- Rejeição de falsos positivos de jurisprudência/citações
- Recorte ponta a ponta com Random Forest e fallback baseado em regras
"""

from __future__ import annotations

from pathlib import Path
import pytest
import numpy as np

from causaganha.decisoes.hybrid_segmenter import (
    HybridDispositifSegmenter,
    DispositifResult,
    normalize_str,
)

ROOT_DIR = Path(__file__).resolve().parent.parent


def test_normalize_str():
    assert normalize_str("AÇÃO CÍVEL") == "acao civel"
    assert normalize_str(None) == ""
    assert normalize_str(123) == ""
    assert normalize_str("   Juiz de Direito   ") == "juiz de direito"


def test_split_document_units_multiline():
    text = "Relatório do processo.\nFundamentação dos fatos.\nAnte o exposto, julgo procedente."
    units = HybridDispositifSegmenter.split_document_units(text)
    assert len(units) == 3
    assert "julgo procedente" in units[2]["text"]
    assert units[0]["start"] == 0
    assert units[2]["end"] == len(text)


def test_split_document_units_flat_text():
    # Texto sem quebras de linha típicas do DJEN
    text = "Relatório do processo. Fundamentação dos fatos e análise jurídica. Ante ao exposto, julgo procedente a ação. Publique-se."
    units = HybridDispositifSegmenter.split_document_units(text)
    assert len(units) >= 3
    assert any("julgo procedente" in u["text"] for u in units)
    # Garante cobertura contínua dos offsets
    assert units[0]["start"] == 0
    assert units[-1]["end"] == len(text)


def test_extract_header_metadata():
    header = (
        "Tribunal de Justiça do Estado de Rondônia. "
        "Apelação Cível n. 7000109-66.2024.8.22.0000. "
        "Relator : Desembargador José Augusto Alves Martins. "
        "Apelante : Nágila Cardoso de Almeida. "
        "Apelado : Energisa Rondônia Distribuidora. "
        "Data de Julgamento: 15/05/2025."
    )
    meta = HybridDispositifSegmenter.extract_header_metadata(header)
    assert "José Augusto" in meta.get("judge_name", "")
    assert "Nágila" in meta.get("polo_ativo", "")
    assert "Energisa" in meta.get("polo_passivo", "")
    assert meta.get("ano") in {"2024", "2025"}
    assert "apelação" in meta.get("classe_processual", "").lower()


def test_extract_features_shape_and_metadata():
    segmenter = HybridDispositifSegmenter()
    meta = {
        "judge_name": "Dr. Fernando Martins",
        "polo_ativo": "Maria da Silva",
        "polo_passivo": "Banco do Brasil S.A.",
        "classe_processual": "Cumprimento de sentença",
        "ano": "2024",
    }
    para = "Ante o exposto, julgo procedente o pedido formulado por Maria da Silva contra o Banco do Brasil S.A."
    feats = segmenter.extract_features(
        paragraph=para,
        para_idx=8,
        total_paras=10,
        char_offset=4000,
        total_chars=5000,
        metadata=meta,
    )
    assert len(feats) == len(HybridDispositifSegmenter.FEATURE_NAMES)
    # has_canonical_anchor deve ser 1.0
    assert feats[3] == 1.0
    # has_citation_warning deve ser 0.0
    assert feats[4] == 0.0
    # has_plaintiff_mention deve ser 1.0 (Maria da Silva)
    assert feats[6] == 1.0
    # has_defendant_mention deve ser 1.0 (Banco do Brasil)
    assert feats[7] == 1.0
    # classe_is_execucao deve ser 1.0 (Cumprimento de sentença)
    assert feats[9] == 1.0
    # Taxonomia: é sentença de procedência (julgo procedente)
    feat_names = HybridDispositifSegmenter.FEATURE_NAMES
    assert feats[feat_names.index("is_macro_sentenca")] == 1.0
    assert feats[feat_names.index("is_macro_acordao")] == 0.0


def test_citation_penalty_flag():
    segmenter = HybridDispositifSegmenter()
    para_citation = "Conforme precedente do STJ no REsp 1.234.567/DF, relator Ministro Fulano, a ementa fixou entendimento."
    feats = segmenter.extract_features(
        paragraph=para_citation,
        para_idx=4,
        total_paras=10,
        char_offset=2000,
        total_chars=5000,
        metadata={},
    )
    # has_citation_warning deve ser 1.0
    assert feats[4] == 1.0
    # Score baseado em regras deve ser fortemente penalizado
    score = segmenter._rule_based_score(feats)
    assert score <= 0.20


def test_predict_with_saved_model():
    model_path = ROOT_DIR / "models/hybrid_dispositif_forest.joblib"
    if not model_path.exists():
        pytest.skip("Modelo treinado não encontrado em models/")

    segmenter = HybridDispositifSegmenter(model_path=model_path)
    assert segmenter.is_fitted is True

    doc_text = (
        "TRIBUNAL DE JUSTIÇA DE RONDÔNIA\n"
        "Apelação Cível n. 1234567-89.2024.8.22.0001\n"
        "Relator: Desembargador Gilberto Barbosa\n\n"
        "RELATÓRIO\n"
        "Trata-se de ação de cobrança ajuizada por João contra Empresa X.\n"
        "O autor alega inadimplemento contratual e requer danos morais e materiais.\n"
        "A requerida apresentou contestação tempestiva sustentando ausência de culpa.\n\n"
        "FUNDAMENTAÇÃO\n"
        "Passo ao mérito. Conforme jurisprudência do STJ no REsp 999/DF, o dano moral exige comprovação.\n"
        "Analisando os autos, verifica-se que o serviço foi prestado a contento.\n\n"
        "DISPOSITIVO\n"
        "Ante o exposto, julgo improcedente o pedido formulado na inicial, resolvendo o mérito nos termos do art. 487, I, do CPC.\n"
        "Condeno o autor ao pagamento das custas processuais e honorários advocatícios fixados em 10% sobre o valor da causa.\n"
        "Publique-se. Registre-se. Intimem-se.\n"
        "Porto Velho, 20 de outubro de 2024.\n"
        "Desembargador Gilberto Barbosa\n"
    )

    res = segmenter.predict(doc_text)
    assert isinstance(res, DispositifResult)
    assert res.start > 0
    assert "julgo improcedente" in res.snippet
    assert res.confidence > 0.50
    assert res.fallback_used is False


def test_rule_based_fallback_unfitted():
    segmenter = HybridDispositifSegmenter()  # sem modelo carregado
    assert segmenter.is_fitted is False

    doc_text = (
        "Ação ordinária. Relatório extenso da causa. "
        "Fundamentação sobre os deveres das partes na relação contratual. "
        "Diante do exposto, julgo procedente a ação para condenar o réu. "
        "Juiz de Direito Dr. Silva."
    )
    res = segmenter.predict(doc_text, max_snippet_chars=50)
    assert isinstance(res, DispositifResult)
    assert len(res.snippet) <= 50
    assert res.confidence > 0.0
