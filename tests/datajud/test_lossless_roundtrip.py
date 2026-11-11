"""Testes de reversibilidade matemática rigorosa (Lossless Roundtrip) para o DataJud.

Garante a invariante fundamental:
    decode(encode(D)) == D
para 100% dos documentos do inventário e das amostras reais.
"""

from __future__ import annotations

import json

from datajud.schema.lossless_codec import LosslessCodec, LosslessVocabulary
from scripts.datajud.benchmark_formats import carregar_colecoes_cnj


def test_lossless_roundtrip_all_documents():
    """Garante reversibilidade estrutural absoluta para todos os 68 documentos."""
    colecoes = carregar_colecoes_cnj()
    assert len(colecoes) > 0, "Nenhuma coleção carregada para teste de reversibilidade"

    vocab = LosslessVocabulary()
    total_docs = 0

    for cnj, docs in colecoes.items():
        for doc in docs:
            total_docs += 1
            # 1. Encode
            compact = LosslessCodec.encode_document(doc, vocab)

            # 2. Decode
            decoded = LosslessCodec.decode_document(compact, cnj, vocab)

            # 3. Asserção estrita de igualdade JSON
            orig_json = json.dumps(doc, sort_keys=True, ensure_ascii=False)
            dec_json = json.dumps(decoded, sort_keys=True, ensure_ascii=False)

            assert dec_json == orig_json, (
                f"Falha de reversibilidade no documento {doc.get('_id')} (CNJ {cnj})"
            )

    assert total_docs >= 68, f"Esperado ao menos 68 documentos, testado: {total_docs}"


def test_lossless_vocabulary_export_and_reload():
    """Valida serialização e desserialização isolada do vocabulário."""
    vocab = LosslessVocabulary()
    id1 = vocab.get_or_add("Sentença")
    id2 = vocab.get_or_add("Despacho")
    id3 = vocab.get_or_add("Sentença")  # repetição deve reusar o id

    assert id1 == id3
    assert id1 != id2

    exported = vocab.export()
    loaded_vocab = LosslessVocabulary.load(exported)

    assert loaded_vocab.get(id1) == "Sentença"
    assert loaded_vocab.get(id2) == "Despacho"
    assert loaded_vocab.get(-1) is None
    assert loaded_vocab.get(9999) is None


def test_lossless_preserves_unexpected_fields():
    """Garante preservação de campos anômalos no envelope ou no _source."""
    vocab = LosslessVocabulary()
    doc_anomalo = {
        "_index": "api_publica_tjcustom",
        "_id": "TJCUSTOM_G1_12345",
        "_score": 42.5,
        "sort": [999999],
        "metadado_envelope_extra": {"origem": "crawler_ia"},
        "_source": {
            "id": "TJCUSTOM_G1_12345",
            "numeroProcesso": "12345",
            "tribunal": "TJCUSTOM",
            "grau": "G1",
            "campo_futuro_cnj": "valor_especial_2027",
            "movimentos": [
                {
                    "codigo": 999,
                    "nome": "Movimento Inédito",
                    "dataHora": "2027-01-01T00:00:00.000Z",
                    "campo_mov_extra": 123,
                    "complementosTabelados": [
                        {
                            "codigo": 1,
                            "nome": "Complemento Inédito",
                            "descricao": "desc",
                            "valor": 99,
                            "campo_comp_extra": "foo",
                        }
                    ],
                }
            ],
        },
    }

    compact = LosslessCodec.encode_document(doc_anomalo, vocab)
    decoded = LosslessCodec.decode_document(compact, "12345", vocab)

    assert json.dumps(decoded, sort_keys=True) == json.dumps(doc_anomalo, sort_keys=True)
