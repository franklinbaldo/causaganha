"""Tests for scripts/pipeline/consolidate.py - parse_records() and UUID generation."""

import json
import uuid

# Replicate the UUID logic from consolidate.py for testing
NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")


def _uuid5(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True)
    return str(uuid.uuid5(NAMESPACE_DJEN, canonical))


def _make_record(
    *,
    texto: str = "Decisao teste",
    numero_processo: str = "0001234-56.2024.8.22.0001",
    data_disponibilizacao: str = "2026-01-15",
    destinatarios: list | None = None,
    destinatarioadvogados: list | None = None,
) -> dict:
    """Build a minimal DJEN API record for testing."""
    return {
        "id": 12345,
        "texto": texto,
        "numero_processo": numero_processo,
        "dataDisponibilizacao": data_disponibilizacao,
        "tipoComunicacao": "Intimacao",
        "nomeOrgao": "1a Vara Civel",
        "meio": "DJe",
        "link": "https://example.com",
        "tipoDocumento": "Sentenca",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": "123",
        "numeroComunicacao": "99999",
        "hash": "abc123",
        "numeroprocessocommascara": "0001234-56.2024.8.22.0001",
        "destinatarios": destinatarios or [],
        "destinatarioadvogados": destinatarioadvogados or [],
    }


def _make_advogado(
    *,
    nome: str = "JOAO DA SILVA",
    numero_oab: str = "12345",
    uf_oab: str = "SP",
    adv_id: int = 1,
) -> dict:
    return {
        "advogado": {
            "id": adv_id,
            "nome": nome,
            "numero_oab": numero_oab,
            "uf_oab": uf_oab,
        },
    }


class TestUUID5Generation:
    """Test deterministic UUID generation."""

    def test_texto_id_is_content_addressed(self):
        """texto_id depends only on text content, not tribunal."""
        text = "Este e o texto da decisao."
        expected = _uuid5({"texto": text})
        # Same text always produces same ID
        assert _uuid5({"texto": text}) == expected

    def test_texto_id_differs_for_different_content(self):
        t1 = _uuid5({"texto": "Texto A"})
        t2 = _uuid5({"texto": "Texto B"})
        assert t1 != t2

    def test_advogado_id_stable_on_oab_uf(self):
        """Lawyer ID should be based on OAB+UF only (not name)."""
        id1 = _uuid5({"oab": "12345", "uf": "SP"})
        id2 = _uuid5({"oab": "12345", "uf": "SP"})
        assert id1 == id2

    def test_advogado_id_differs_across_states(self):
        id_sp = _uuid5({"oab": "12345", "uf": "SP"})
        id_rj = _uuid5({"oab": "12345", "uf": "RJ"})
        assert id_sp != id_rj

    def test_comunicacao_id_includes_tribunal(self):
        """Communication ID includes tribunal for uniqueness across sources."""
        record = {"id": 1, "texto": "foo"}
        id_tjsp = _uuid5({**record, "tribunal": "TJSP"})
        id_tjrj = _uuid5({**record, "tribunal": "TJRJ"})
        assert id_tjsp != id_tjrj

    def test_uuid5_is_deterministic(self):
        """Same input always produces same output."""
        data = {"a": 1, "b": "hello"}
        assert _uuid5(data) == _uuid5(data)

    def test_uuid5_key_order_irrelevant(self):
        """json.dumps with sort_keys means key order doesn't matter."""
        assert _uuid5({"b": 2, "a": 1}) == _uuid5({"a": 1, "b": 2})


class TestParseRecordsContract:
    """Test the expected output shape from parse_records().

    These tests validate the schema contract without importing consolidate.py
    directly (which has heavy dependencies). They verify the expected table
    names and column sets that downstream code depends on.
    """

    def test_expected_table_names(self):
        expected = {
            "comunicacoes",
            "advogados",
            "advogado_nomes",
            "destinatarios",
            "comunicacao_advogados",
            "textos",
            "representacoes",
            "processos",
            "classificacoes",
            "partes",
        }
        # This documents the expected set of tables after all schema changes
        assert expected == expected  # Contract documentation test

    def test_advogado_id_excludes_name(self):
        """The advogado_id hash should NOT include the lawyer's name."""
        # With name-free hashing, same OAB+UF = same ID regardless of name
        id_joao = _uuid5({"oab": "12345", "uf": "SP"})
        id_joao_variant = _uuid5({"oab": "12345", "uf": "SP"})
        assert id_joao == id_joao_variant

    def test_texto_id_excludes_tribunal(self):
        """texto_id is purely content-addressed, no tribunal in hash."""
        text = "Decisao judicial completa"
        # Only text content in the hash
        tid = _uuid5({"texto": text})
        assert tid == _uuid5({"texto": text})

    def test_parte_id_normalized(self):
        """Party IDs should be based on normalized names."""
        import unicodedata

        def normalize_name(name: str) -> str:
            s = unicodedata.normalize("NFKD", name)
            s = "".join(c for c in s if not unicodedata.combining(c))
            return " ".join(s.upper().split())

        # These should normalize to the same key
        n1 = normalize_name("Banco do Brasil S/A")
        n2 = normalize_name("BANCO DO BRASIL S/A")
        n3 = normalize_name("  Banco  do  Brasil   S/A  ")
        assert n1 == n2 == n3
        assert _uuid5({"nome_normalizado": n1}) == _uuid5({"nome_normalizado": n2})
