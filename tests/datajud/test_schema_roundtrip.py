"""Testes de integridade do inventário multíndice e roundtrip sem perda (Issue #1710)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datajud.schema import __file__ as schema_pkg_file
from scripts.datajud.benchmark_formats import (
    FlatBuffersPacker,
    carregar_colecoes_cnj,
)


def test_schema_fbs_file_exists():
    """Valida que o schema FlatBuffers oficial existe no repositório."""
    schema_path = Path(schema_pkg_file).parent / "processo.fbs"
    assert schema_path.exists(), f"Schema FlatBuffers não encontrado em {schema_path}"
    content = schema_path.read_text(encoding="utf-8")
    assert "table DocumentoDataJud" in content
    assert "table ProcessoCNJCollection" in content
    assert "campos_desconhecidos_json" in content


def test_multigrau_cardinality_preservation():
    """Garante que CNJs com múltiplos graus (G1 e G2) não são deduplicados ou sobrescritos."""
    colecoes = carregar_colecoes_cnj()
    
    # Encontra casos com multigrau
    casos_multigrau = {cnj: docs for cnj, docs in colecoes.items() if len(docs) > 1}
    assert len(casos_multigrau) > 0, "Deveria haver pelo menos um caso multigrau na fixture real"
    
    for cnj, docs in casos_multigrau.items():
        graus = {d.get("_source", {}).get("grau") for d in docs}
        assert len(graus) > 1, f"CNJ {cnj} possui múltiplos docs mas mesmo grau: {graus}"
        
        # Empacota coleção inteira no FlatBuffers
        buf = FlatBuffersPacker.pack_collection(cnj, docs)
        assert len(buf) > 0
        
        # Recupera primeiro documento
        doc0 = FlatBuffersPacker.unpack_raw_doc(buf, 0)
        assert doc0["_id"] == docs[0]["_id"]
        assert doc0["_source"]["numeroProcesso"] == cnj


def test_zero_loss_roundtrip_all_fixtures():
    """Valida roundtrip estrutural com 100% de integridade estrutural em todos os registros."""
    colecoes = carregar_colecoes_cnj()
    
    for cnj, docs in colecoes.items():
        buf = FlatBuffersPacker.pack_collection(cnj, docs)
        for idx, doc_orig in enumerate(docs):
            doc_rec = FlatBuffersPacker.unpack_raw_doc(buf, idx)
            assert doc_rec["_id"] == doc_orig["_id"]
            assert doc_rec["_index"] == doc_orig["_index"]
            assert doc_rec["_source"] == doc_orig["_source"]
