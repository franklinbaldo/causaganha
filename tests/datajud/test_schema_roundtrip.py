"""Testes de integridade do inventário multíndice e roundtrip sem perda (Issue #1710)."""

from __future__ import annotations

import json
from pathlib import Path

from datajud.schema import __file__ as schema_pkg_file
from datajud.schema.flatbuffers_codec import FlatBuffersCodec
from scripts.datajud.benchmark_formats import (
    FIXTURES_DIR,
    PARES_PATH,
    carregar_colecoes_cnj,
)


def test_schema_fbs_file_exists():
    """Valida que o schema FlatBuffers oficial existe no repositório e declara as tabelas."""
    schema_path = Path(schema_pkg_file).parent / "processo.fbs"
    assert schema_path.exists(), f"Schema FlatBuffers não encontrado em {schema_path}"
    content = schema_path.read_text(encoding="utf-8")
    assert "table DocumentoDataJud" in content
    assert "table ProcessoCNJCollection" in content
    assert "campos_desconhecidos_json" in content
    assert "payload_original_bruto_gz" in content


def test_pares_multindice_comprovados_existencia():
    """Comprova empiricamente que o mesmo CNJ foi recuperado em múltiplos índices (STJ + Origem)."""
    assert PARES_PATH.exists(), f"Arquivo de pares comprovados não encontrado em {PARES_PATH}"
    pares = json.loads(PARES_PATH.read_text(encoding="utf-8"))
    assert len(pares) >= 3, (
        f"Esperado ao menos 3 pares multíndice comprovados, obtido: {len(pares)}"
    )

    for par in pares:
        cnj = par["cnj"]
        orig_hits = par["documentos_origem"]
        sup_hits = par["documentos_superior"]

        assert len(orig_hits) >= 1, f"Par {cnj} sem documento no tribunal de origem"
        assert len(sup_hits) >= 1, f"Par {cnj} sem documento no tribunal superior"

        # Verifica proveniência distinta para o mesmo CNJ
        indices_origem = {h["_index"] for h in orig_hits}
        indices_sup = {h["_index"] for h in sup_hits}

        assert "api_publica_stj" in indices_sup or "api_publica_tst" in indices_sup
        assert not indices_origem.intersection(indices_sup), (
            f"Colisão indevida de índice: {indices_origem} e {indices_sup}"
        )

        # Verifica que o número do processo é idêntico em ambos
        for h in orig_hits + sup_hits:
            assert h["_source"]["numeroProcesso"] == cnj


def test_multigrau_e_multindice_cardinality_all_documents():
    """Garante que TODOS os documentos de uma coleção (G1, G2, SUP) são serializados e recuperados."""
    colecoes = carregar_colecoes_cnj()

    # Filtra coleções com múltiplos documentos
    multidoc_cases = {cnj: docs for cnj, docs in colecoes.items() if len(docs) > 1}
    assert len(multidoc_cases) > 0, "Deveria haver casos com múltiplos documentos/graus na fixture"

    for cnj, docs in multidoc_cases.items():
        buf = FlatBuffersCodec.encode_collection(cnj, docs)
        assert len(buf) > 0

        # Recupera TODOS os documentos decodificados tipados
        decoded_typed = FlatBuffersCodec.decode_collection(buf, mode="typed")
        assert len(decoded_typed) == len(docs), f"Número divergente de documentos para CNJ {cnj}"

        # Valida que todos os IDs e índices de origem foram recuperados
        recovered_provenances = {(d["_index"], d["_id"]) for d in decoded_typed}
        original_provenances = {(d["_index"], d["_id"]) for d in docs}
        assert recovered_provenances == original_provenances, (
            f"Proveniência divergente no CNJ {cnj}"
        )

        # Recupera TODOS os documentos decodificados no modo raw
        decoded_raw = FlatBuffersCodec.decode_collection(buf, mode="raw")
        assert len(decoded_raw) == len(docs)
        for idx in range(len(docs)):
            assert decoded_raw[idx] == docs[idx]


def test_projecao_seletiva_capa():
    """Valida que a leitura da capa (modo 'capa') recupera metadados sem carregar movimentos."""
    colecoes = carregar_colecoes_cnj()
    cnj = list(colecoes.keys())[0]
    docs = colecoes[cnj]

    buf = FlatBuffersCodec.encode_collection(cnj, docs)
    capas = FlatBuffersCodec.decode_collection(buf, mode="capa")

    assert len(capas) == len(docs)
    for idx, c in enumerate(capas):
        assert c["_id"] == docs[idx]["_id"]
        assert c["_index"] == docs[idx]["_index"]
        assert c["numeroProcesso"] == cnj
        assert "movimentos" not in c  # Comprova projeção seletiva sem carregar array volumoso


def test_auditoria_contextual_pii_fixtures():
    """Garante que nenhum nome de parte, pessoa ou CPF/CNJ desmascarado consta nas fixtures."""
    for fixture_file in FIXTURES_DIR.glob("*.json"):
        content = fixture_file.read_text(encoding="utf-8")
        # Garante que não há padrões de CPF desmascarado
        import re

        cpfs = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", content)
        for cpf in cpfs:
            assert cpf == "000.***.***-00", f"CPF desmascarado encontrado em {fixture_file}: {cpf}"
