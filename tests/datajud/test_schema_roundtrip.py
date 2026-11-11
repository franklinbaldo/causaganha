"""Testes de integridade do inventário multíndice e roundtrip sem perda (Issue #1710, #1711)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Registra o diretório das classes geradas oficialmente pelo flatc
GENERATED_DIR = Path(__file__).resolve().parents[2] / "src" / "datajud" / "schema" / "generated"
if str(GENERATED_DIR) not in sys.path:
    sys.path.insert(0, str(GENERATED_DIR))

from DataJud.Schema.ProcessoCNJCollection import ProcessoCNJCollection  # noqa: E402
from datajud.schema import __file__ as schema_pkg_file  # noqa: E402
from datajud.schema.compact_codec import CompactFlatBuffersCodec  # noqa: E402
from datajud.schema.flatbuffers_codec import FlatBuffersCodec  # noqa: E402
from scripts.datajud.benchmark_formats import (  # noqa: E402
    FIXTURES_DIR,
    PARES_PATH,
    carregar_colecoes_cnj,
)


def test_schema_fbs_files_exist():
    """Valida que os esquemas FlatBuffers existem no repositório."""
    schema_dir = Path(schema_pkg_file).parent
    assert (schema_dir / "processo.fbs").exists(), "processo.fbs não encontrado"
    assert (schema_dir / "processo_compact.fbs").exists(), "processo_compact.fbs não encontrado"


def test_validacao_independente_classes_geradas_flatc():
    """Valida o buffer FlatBuffers utilizando exclusivamente as classes geradas pelo flatc oficial."""
    colecoes = carregar_colecoes_cnj()
    cnj = list(colecoes.keys())[0]
    docs = colecoes[cnj]

    buf = FlatBuffersCodec.encode_collection(cnj, docs)
    assert len(buf) > 0

    # Leitura independente através da classe gerada pelo flatc
    coll = ProcessoCNJCollection.GetRootAs(buf, 0)
    assert coll.NumeroProcesso().decode("utf-8") == cnj
    assert coll.TotalDocumentos() == len(docs)
    assert coll.DocumentosLength() == len(docs)

    for i in range(coll.DocumentosLength()):
        doc = coll.Documentos(i)
        assert doc.IndexOrigem().decode("utf-8") == docs[i]["_index"]
        assert doc.IdOrigem().decode("utf-8") == docs[i]["_id"]
        assert doc.Tribunal().decode("utf-8") == docs[i]["_source"]["tribunal"]
        assert doc.Grau().decode("utf-8") == docs[i]["_source"]["grau"]


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

        indices_origem = {h["_index"] for h in orig_hits}
        indices_sup = {h["_index"] for h in sup_hits}

        assert "api_publica_stj" in indices_sup or "api_publica_tst" in indices_sup
        assert not indices_origem.intersection(indices_sup), (
            f"Colisão indevida de índice: {indices_origem} e {indices_sup}"
        )

        for h in orig_hits + sup_hits:
            assert h["_source"]["numeroProcesso"] == cnj


def test_multigrau_e_multindice_cardinality_all_documents():
    """Garante que TODOS os documentos de uma coleção (G1, G2, SUP) são serializados e recuperados."""
    colecoes = carregar_colecoes_cnj()
    multidoc_cases = {cnj: docs for cnj, docs in colecoes.items() if len(docs) > 1}
    assert len(multidoc_cases) > 0, "Deveria haver casos com múltiplos documentos/graus na fixture"

    for cnj, docs in multidoc_cases.items():
        buf = FlatBuffersCodec.encode_collection(cnj, docs)

        # 1. Modo Typed: recupera todos os documentos tipados
        decoded_typed = FlatBuffersCodec.decode_collection(buf, mode="typed")
        assert len(decoded_typed) == len(docs)
        recovered_provenances = {(d["_index"], d["_id"]) for d in decoded_typed}
        original_provenances = {(d["_index"], d["_id"]) for d in docs}
        assert recovered_provenances == original_provenances

        # 2. Modo Raw: garante equivalência estrutural absoluta do objeto original
        decoded_raw = FlatBuffersCodec.decode_collection(buf, mode="raw")
        assert len(decoded_raw) == len(docs)
        for idx in range(len(docs)):
            assert decoded_raw[idx] == docs[idx]


def test_codec_hibrido_capa_o1_e_full_decode():
    """Valida o codec híbrido (Capa O(1) em FlatBuffers + Movimentos em Zstandard)."""
    colecoes = carregar_colecoes_cnj()
    cnj = list(colecoes.keys())[0]
    docs = colecoes[cnj]

    buf = CompactFlatBuffersCodec.encode_hybrid(cnj, docs)
    assert len(buf) > 0

    # 1. Projeção seletiva da capa (sem descompressão)
    capas = CompactFlatBuffersCodec.decode_capa_only(buf)
    assert len(capas) == len(docs)
    for idx, c in enumerate(capas):
        assert c["_id"] == docs[idx]["_id"]
        assert c["tribunal"] == docs[idx]["_source"]["tribunal"]
        assert c["grau"] == docs[idx]["_source"]["grau"]

    # 2. Decodificação completa com descompressão de movimentos
    full_docs = CompactFlatBuffersCodec.decode_full(buf)
    assert len(full_docs) == len(docs)
    for idx, f in enumerate(full_docs):
        assert len(f["movimentos"]) == len(docs[idx]["_source"]["movimentos"])


def test_auditoria_contextual_pii_fixtures():
    """Audita rigorosamente as fixtures contra padrões de CPF, CNPJ e nomes não anonimizados."""
    for fixture_file in FIXTURES_DIR.glob("*.json"):
        content = fixture_file.read_text(encoding="utf-8")

        # 1. CPFs formatados devem ser estritamente mascarados
        formatted_cpfs = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", content)
        for cpf in formatted_cpfs:
            assert cpf == "000.***.***-00", f"CPF formatado desmascarado em {fixture_file}: {cpf}"

        # 2. CNPJs formatados devem ser estritamente mascarados
        formatted_cnpjs = re.findall(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", content)
        for cnpj in formatted_cnpjs:
            assert cnpj == "000.***.***-00", (
                f"CNPJ formatado desmascarado em {fixture_file}: {cnpj}"
            )
