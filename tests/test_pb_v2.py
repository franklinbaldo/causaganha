"""Tests for lossless PB v2 DJEN codec."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from causaganha.consolidate.pb_v2 import (
    TemplateHashCodec,
    convert_djen_zip_to_pb_zip,
    decode_pb_zip_bytes,
    encode_records_to_pb_zip_bytes,
)


def _sample_records() -> list[dict]:
    return [
        {
            "id": 778704990,
            "data_disponibilizacao": "2026-11-09",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "Porto Velho - 4ª Vara Criminal",
            "texto": "INTIMAÇÃO DA SENTENÇA. Prazo de 15 dias úteis.\n\tCom § 1º e art. 5º.",
            "numero_processo": "70726450920238220001",
            "meio": "D",
            "link": "https://pjepg.tjro.jus.br/pje/Processo/ConsultaDocumento/listView.seam?x=123456",
            "tipoDocumento": "Decisão",
            "nomeClasse": "AÇÃO PENAL - PROCEDIMENTO ORDINÁRIO",
            "codigoClasse": "283",
            "numeroComunicacao": 1,
            "ativo": True,
            "hash": "JKOdGxm7gYmLtXh1T7mM5lZy5DBkl2",
            "status": "P",
            "motivo_cancelamento": None,
            "data_cancelamento": None,
            "datadisponibilizacao": "09/11/2026",
            "dataenvio": "06/11/2026",
            "destinatarios": [
                {"nome": "ANTONIO MARCOS", "polo": "P", "comunicacao_id": 778704990},
            ],
            "destinatarioadvogados": [
                {
                    "id": 1470234109,
                    "comunicacao_id": 778704990,
                    "advogado_id": 1063997,
                    "created_at": "2026-11-06 01:28:45",
                    "updated_at": "2026-11-06 01:28:45",
                    "advogado": {
                        "id": 1063997,
                        "nome": "JOAO VICTOR",
                        "numero_oab": "12858",
                        "uf_oab": "RO",
                    },
                },
            ],
        },
        {
            "id": 778704991,
            "data_disponibilizacao": "2026-11-09",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Edital",
            "nomeOrgao": "1ª Vara Cível",
            "texto": "",
            "numero_processo": "LEGACY-123",
            "meio": "E",
            "link": "https://example.org/doc/99",
            "tipoDocumento": "Edital",
            "nomeClasse": "PROCEDIMENTO COMUM CÍVEL",
            "codigoClasse": "7",
            "numeroComunicacao": 2,
            "ativo": False,
            "hash": "bgeNaPz7wR5OtEC8T9e5oDZBMJpDrL",
            "status": "C",
            "motivo_cancelamento": "Erro material",
            "data_cancelamento": "2026-11-10",
            "datadisponibilizacao": "10/11/2026",
            "dataenvio": "08/11/2026",
            "destinatarios": [
                {"nome": "EMPRESA X", "polo": "A", "comunicacao_id": 999},
            ],
            "destinatarioadvogados": [
                {
                    "id": 1470234110,
                    "comunicacao_id": 888,
                    "advogado_id": 777,
                    "created_at": "2026-11-06 01:28:45",
                    "updated_at": "2026-11-07 10:00:00",
                    "advogado": {
                        "id": 1063997,
                        "nome": "JOAO VICTOR",
                        "numero_oab": "12858",
                        "uf_oab": "RO",
                    },
                },
            ],
        },
    ]


@pytest.mark.parametrize("mode", ["stored", "deflated", "zstd", "zstd_dict"])
def test_pb_v2_roundtrip_all_modes(mode: str) -> None:
    records = _sample_records()
    encoded = encode_records_to_pb_zip_bytes(records, mode=mode)  # type: ignore[arg-type]
    decoded = decode_pb_zip_bytes(encoded)
    assert decoded == records


def test_convert_djen_zip_to_pb_zip(tmp_path: Path) -> None:
    records = _sample_records()
    src_zip = tmp_path / "djen-2026-11-09-TJRO.zip"
    dst_zip = tmp_path / "djen-2026-11-09-TJRO.pb.zip"
    with zipfile.ZipFile(src_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("page1.json", json.dumps({"items": records}))

    stats = convert_djen_zip_to_pb_zip(src_zip, dst_zip, mode="zstd_dict", verify_roundtrip=True)
    assert stats["records"] == 2
    assert dst_zip.exists()
    assert decode_pb_zip_bytes(dst_zip.read_bytes()) == records


def test_template_hash_codec_lossless() -> None:
    hashes = [
        "QpOqvB2l63OtMxU9TXG5Jj6yPD35na",
        "QpOqvB2lZ3OtebH9TXG5JjZyPD35na",
        "KOdGxm7gZmLtXXC1T7mM5l6y5DBkl2",
        "KOdGxm7g6mLtdXT1T7mM5lRy5DBkl2",
        "NON_STANDARD_HASH_FALLBACK_LITERAL",
    ]
    codec = TemplateHashCodec.train(hashes, min_occurrences=2)
    assert len(codec.templates) >= 1

    for h in hashes:
        tid, var_payload = codec.encode(h)
        reconstructed = codec.decode(tid, var_payload)
        assert reconstructed == h

