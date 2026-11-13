"""Tests for lossless PB v2 DJEN codec."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from causaganha.consolidate.pb_v2 import (
    BatchDict,
    TemplateHashCodec,
    build_secondary_hash_index,
    convert_djen_zip_to_pb_zip,
    decode_pb_zip_bytes,
    encode_records_to_pb_zip_bytes,
    read_secondary_hash_index,
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


def test_edge_cases_integrity() -> None:
    records = [
        {
            "id": 1,
            "hash": "H11111111111111111111111111111",
            "data_disponibilizacao": None,
            "siglaTribunal": None,
            "tipoComunicacao": None,
            "nomeOrgao": None,
            "texto": None,  # Explicit None vs ""
            "numero_processo": None,
            "meio": None,
            "link": None,
            "tipoDocumento": None,
            "nomeClasse": None,
            "codigoClasse": None,
            "numeroComunicacao": 1,
            "ativo": None,  # Explicit None vs False
            "status": None,
            "motivo_cancelamento": None,
            "data_cancelamento": None,
            "datadisponibilizacao": None,
            "dataenvio": None,
            "destinatarios": [
                {},  # Empty recipient dict
                {"nome": None, "polo": None, "comunicacao_id": 1},
                {"nome": "", "polo": "", "comunicacao_id": None},
            ],
            "destinatarioadvogados": [
                {
                    "id": 101,
                    "comunicacao_id": 1,
                    "advogado_id": 501,
                    "created_at": "2026-11-09 10:00:00",
                    "updated_at": None,  # Must stay None!
                    "advogado": None,
                },
                {
                    "id": 102,
                    "comunicacao_id": 1,
                    "advogado_id": 502,
                    "created_at": "2026-11-09 10:00:00",
                    "updated_at": "2026-11-09 10:00:00",  # Shared ts
                    "advogado": {
                        "id": 502,
                        "nome": "",  # Empty string
                        "numero_oab": None,  # None
                        "uf_oab": "",  # Empty string
                    },
                },
                {
                    "id": 103,
                    "comunicacao_id": 1,
                    "advogado_id": 503,
                    "created_at": "2026-11-09 10:00:00",
                    "updated_at": "2026-11-09 12:00:00",  # Different ts
                    "advogado": {
                        "id": 503,
                        "nome": None,  # None
                        "numero_oab": "12345",  # Valid string
                        "uf_oab": None,  # None
                    },
                },
            ],
        },
        {
            "id": 2,
            "hash": "H22222222222222222222222222222",
            "data_disponibilizacao": "2026-11-09",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "Vara 1",
            "texto": "",  # Explicit empty string
            "numero_processo": "70726450920238220001",
            "meio": "D",
            "link": "https://example.com/doc",
            "tipoDocumento": "Decisão",
            "nomeClasse": "Procedimento",
            "codigoClasse": "1",
            "numeroComunicacao": 2,
            "ativo": False,  # Explicit False
            "status": "P",
            "motivo_cancelamento": None,
            "data_cancelamento": None,
            "datadisponibilizacao": "09/11/2026",
            "dataenvio": "06/11/2026",
            "destinatarios": [],
            "destinatarioadvogados": [],
        },
    ]

    for mode in ["stored", "zstd_dict"]:
        encoded = encode_records_to_pb_zip_bytes(records, mode=mode)  # type: ignore[arg-type]
        decoded = decode_pb_zip_bytes(encoded)
        # Verify first item
        r1 = decoded[0] if decoded[0]["id"] == 1 else decoded[1]
        assert r1["texto"] is None
        assert r1["ativo"] is None
        assert len(r1["destinatarios"]) == 3
        assert r1["destinatarios"][0] == {"nome": None, "polo": None, "comunicacao_id": None}
        assert r1["destinatarios"][1] == {"nome": None, "polo": None, "comunicacao_id": 1}
        assert r1["destinatarios"][2] == {"nome": "", "polo": "", "comunicacao_id": None}

        da1 = r1["destinatarioadvogados"][0]
        assert da1["created_at"] == "2026-11-09 10:00:00"
        assert da1["updated_at"] is None  # Integrity: no false mutation to created_at!

        da2 = r1["destinatarioadvogados"][1]
        assert da2["updated_at"] == "2026-11-09 10:00:00"
        assert da2["advogado"]["nome"] == ""
        assert da2["advogado"]["numero_oab"] is None
        assert da2["advogado"]["uf_oab"] == ""

        da3 = r1["destinatarioadvogados"][2]
        assert da3["updated_at"] == "2026-11-09 12:00:00"
        assert da3["advogado"]["nome"] is None
        assert da3["advogado"]["numero_oab"] == "12345"
        assert da3["advogado"]["uf_oab"] is None

        # Verify second item
        r2 = decoded[1] if decoded[1]["id"] == 2 else decoded[0]
        assert r2["texto"] == ""
        assert r2["ativo"] is False


def test_duplicate_hash_rejection() -> None:
    rec1 = {
        "id": 1,
        "hash": "DUPLICATE_HASH_12345678901234",
        "texto": "First version",
    }
    rec2_identical = {
        "id": 1,
        "hash": "DUPLICATE_HASH_12345678901234",
        "texto": "First version",
    }
    rec2_conflicting = {
        "id": 2,
        "hash": "DUPLICATE_HASH_12345678901234",
        "texto": "Different version",
    }

    with pytest.raises(ValueError, match="Duplicate record detected"):
        encode_records_to_pb_zip_bytes([rec1, rec2_identical], mode="stored")

    with pytest.raises(ValueError, match="Conflicting duplicate record"):
        encode_records_to_pb_zip_bytes([rec1, rec2_conflicting], mode="stored")


def test_secondary_hash_index_roundtrip() -> None:
    hashes = [
        "QpOqvB2l63OtMxU9TXG5Jj6yPD35na",
        "QpOqvB2lZ3OtebH9TXG5JjZyPD35na",
        "KOdGxm7gZmLtXXC1T7mM5l6y5DBkl2",
        "KOdGxm7g6mLtdXT1T7mM5lRy5DBkl2",
        "FALLBACK_LITERAL_HASH_12345678",
        "SHORT_HASH",
    ]
    idx_bytes = build_secondary_hash_index(hashes)
    assert len(idx_bytes) > 0
    recovered = read_secondary_hash_index(idx_bytes)
    assert recovered == hashes


def test_batch_dict_populates_hash_templates() -> None:
    records = [
        {"id": 1, "hash": "QpOqvB2l63OtMxU9TXG5Jj6yPD35na", "texto": "A"},
        {"id": 2, "hash": "QpOqvB2lZ3OtebH9TXG5JjZyPD35na", "texto": "B"},
    ]
    zip_bytes = encode_records_to_pb_zip_bytes(records, mode="stored")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        bd = BatchDict.from_pb(zf.read("_dict.pb"))
        assert len(bd.hash_templates) >= 1
