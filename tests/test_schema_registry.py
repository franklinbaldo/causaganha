"""Schema registry snapshot tests.

Ensures TABLE_SCHEMAS in transforms.py stays in sync with the schema
registry, and that schema versions are never modified after publication.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest

from causaganha.consolidate.schema_registry import (
    CURRENT_VERSION,
    SCHEMA_REGISTRY,
    get_current_schema,
    get_schema,
    kv_metadata_for_export,
    kv_metadata_sql_fragment,
)
from causaganha.consolidate.transforms import TABLE_SCHEMAS, TABLES
from causaganha.consolidate.validation import all_passed, validate_parquet


class TestSchemaRegistryConsistency:
    """TABLE_SCHEMAS in transforms.py must match the current registry version."""

    def test_all_tables_present_in_registry(self) -> None:
        schema = get_current_schema()
        for table_name in TABLES:
            assert table_name in schema.tables, (
                f"Table '{table_name}' in TABLES but missing from registry "
                f"version {CURRENT_VERSION}"
            )

    def test_all_registry_tables_present_in_transforms(self) -> None:
        schema = get_current_schema()
        for table_name in schema.tables:
            assert table_name in TABLE_SCHEMAS, (
                f"Table '{table_name}' in registry but missing from TABLE_SCHEMAS"
            )

    def test_schemas_match_field_by_field(self) -> None:
        schema = get_current_schema()
        for table_name in TABLES:
            registry_schema = schema.tables[table_name]
            transforms_schema = TABLE_SCHEMAS[table_name]
            registry_fields = dict(registry_schema.items())
            transforms_fields = dict(transforms_schema.items())
            assert registry_fields == transforms_fields, (
                f"Schema mismatch for '{table_name}' between registry "
                f"({CURRENT_VERSION}) and TABLE_SCHEMAS.\n"
                f"Registry: {registry_fields}\n"
                f"Transforms: {transforms_fields}"
            )


class TestSchemaVersioning:
    def test_current_version_exists(self) -> None:
        assert CURRENT_VERSION in SCHEMA_REGISTRY

    def test_get_schema_returns_correct_version(self) -> None:
        sv = get_schema(CURRENT_VERSION)
        assert sv.version == CURRENT_VERSION

    def test_get_schema_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            get_schema("99.99.99")

    def test_schema_version_is_semver(self) -> None:
        for version in SCHEMA_REGISTRY:
            parts = version.split(".")
            assert len(parts) == 3, f"Version '{version}' is not semver"
            for part in parts:
                assert part.isdigit(), f"Version '{version}' has non-numeric part"


class TestKVMetadata:
    def test_kv_metadata_contains_version(self) -> None:
        meta = kv_metadata_for_export("djen-2026-06-01")
        assert meta["causaganha.schema_version"] == CURRENT_VERSION

    def test_kv_metadata_contains_item_id(self) -> None:
        meta = kv_metadata_for_export("djen-2026-06-01")
        assert meta["causaganha.item_id"] == "djen-2026-06-01"

    def test_kv_sql_fragment_parseable(self) -> None:
        fragment = kv_metadata_sql_fragment("djen-test")
        assert "KV_METADATA" in fragment
        assert CURRENT_VERSION in fragment

    def test_kv_metadata_roundtrips_through_duckdb(self) -> None:
        con = duckdb.connect()
        con.execute("CREATE TABLE t AS SELECT 1 AS x")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.parquet"
            fragment = kv_metadata_sql_fragment("djen-roundtrip")
            con.execute(f"COPY t TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, {fragment})")
            kv = con.execute(f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall()
            kv_dict = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in kv
            }
            assert kv_dict["causaganha.schema_version"] == CURRENT_VERSION
            assert kv_dict["causaganha.item_id"] == "djen-roundtrip"
        con.close()


class TestValidation:
    @pytest.fixture
    def valid_comunicacoes_parquet(self, tmp_path: Path) -> Path:
        con = duckdb.connect()
        fragment = kv_metadata_sql_fragment("djen-2026-06-01")
        con.execute("""
            CREATE TABLE comunicacoes AS SELECT
                'uuid-1' AS id,
                '12345' AS original_id,
                'TJRO' AS tribunal,
                '00012345678901234567' AS numero_processo,
                '0001234-56.2026.8.26.0100' AS numero_processo_mascara,
                DATE '2026-06-01' AS data_disponibilizacao,
                'Intimação' AS tipo_comunicacao,
                '1ª Vara' AS nome_orgao,
                'D' AS meio,
                'https://x' AS link,
                'Sentença' AS tipo_documento,
                'Comum' AS nome_classe,
                '7' AS codigo_classe,
                '1' AS numero_comunicacao,
                'abc123' AS hash,
                CURRENT_TIMESTAMP AS processed_at,
                'texto-uuid' AS texto_id,
                2026 AS p_ano,
                6 AS p_mes,
                'djen-2026-06-01' AS p_item_ia
        """)
        path = tmp_path / "comunicacoes.parquet"
        con.execute(f"COPY comunicacoes TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, {fragment})")
        con.close()
        return path

    def test_valid_parquet_passes(self, valid_comunicacoes_parquet: Path) -> None:
        result = validate_parquet(valid_comunicacoes_parquet, "comunicacoes")
        assert result.passed, f"Unexpected errors: {result.errors}"

    def test_missing_column_blocks(self, tmp_path: Path) -> None:
        con = duckdb.connect()
        con.execute("CREATE TABLE t AS SELECT 'x' AS id, 'TJRO' AS tribunal")
        path = tmp_path / "comunicacoes.parquet"
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")
        con.close()
        result = validate_parquet(path, "comunicacoes", check_kv_metadata=False)
        assert not result.passed
        assert any("missing columns" in e for e in result.errors)

    def test_nonexistent_file_blocks(self, tmp_path: Path) -> None:
        result = validate_parquet(tmp_path / "nope.parquet", "comunicacoes")
        assert not result.passed

    def test_classificacoes_validates_outcomes(self, tmp_path: Path) -> None:
        con = duckdb.connect()
        con.execute("""
            CREATE TABLE classificacoes AS SELECT
                'tid' AS texto_id,
                'keyword_v1' AS metodo,
                'INVALID_OUTCOME' AS outcome,
                'sentença' AS decision_type,
                NULL AS winner_advogado_id,
                NULL AS loser_advogado_id,
                0.5 AS confidence,
                CURRENT_TIMESTAMP AS classified_at
        """)
        path = tmp_path / "classificacoes.parquet"
        con.execute(f"COPY classificacoes TO '{path}' (FORMAT PARQUET)")
        con.close()
        result = validate_parquet(path, "classificacoes", check_kv_metadata=False)
        assert not result.passed
        assert any("invalid outcomes" in e for e in result.errors)

    def test_missing_kv_metadata_blocks(self, tmp_path: Path) -> None:
        con = duckdb.connect()
        con.execute("CREATE TABLE t AS SELECT 'uuid-1' AS id, 'TJRO' AS tribunal")
        path = tmp_path / "comunicacoes.parquet"
        con.execute(f"COPY t TO '{path}' (FORMAT PARQUET)")
        con.close()
        result = validate_parquet(path, "comunicacoes", check_kv_metadata=True)
        assert not result.passed
        assert any("Missing causaganha.schema_version" in e for e in result.errors)

    def test_extra_columns_block(self, tmp_path: Path) -> None:
        con = duckdb.connect()
        fragment = kv_metadata_sql_fragment("djen-test")
        con.execute("""
            CREATE TABLE comunicacoes AS SELECT
                'uuid-1' AS id,
                '12345' AS original_id,
                'TJRO' AS tribunal,
                '00012345678901234567' AS numero_processo,
                '0001234-56.2026.8.26.0100' AS numero_processo_mascara,
                DATE '2026-06-01' AS data_disponibilizacao,
                'Intimação' AS tipo_comunicacao,
                '1ª Vara' AS nome_orgao,
                'D' AS meio,
                'https://x' AS link,
                'Sentença' AS tipo_documento,
                'Comum' AS nome_classe,
                '7' AS codigo_classe,
                '1' AS numero_comunicacao,
                'abc123' AS hash,
                CURRENT_TIMESTAMP AS processed_at,
                'texto-uuid' AS texto_id,
                2026 AS p_ano,
                6 AS p_mes,
                'djen-2026-06-01' AS p_item_ia,
                'SURPRISE' AS rogue_column
        """)
        path = tmp_path / "comunicacoes.parquet"
        con.execute(f"COPY comunicacoes TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, {fragment})")
        con.close()
        result = validate_parquet(path, "comunicacoes")
        assert not result.passed
        assert any("extra columns" in e for e in result.errors)

    def test_unknown_tribunal_blocks(self, tmp_path: Path) -> None:
        con = duckdb.connect()
        fragment = kv_metadata_sql_fragment("djen-test")
        con.execute("""
            CREATE TABLE comunicacoes AS SELECT
                'uuid-1' AS id,
                '12345' AS original_id,
                'BADTRIB' AS tribunal,
                '00012345678901234567' AS numero_processo,
                '0001234-56.2026.8.26.0100' AS numero_processo_mascara,
                DATE '2026-06-01' AS data_disponibilizacao,
                'Intimação' AS tipo_comunicacao,
                '1ª Vara' AS nome_orgao,
                'D' AS meio,
                'https://x' AS link,
                'Sentença' AS tipo_documento,
                'Comum' AS nome_classe,
                '7' AS codigo_classe,
                '1' AS numero_comunicacao,
                'abc123' AS hash,
                CURRENT_TIMESTAMP AS processed_at,
                'texto-uuid' AS texto_id,
                2026 AS p_ano,
                6 AS p_mes,
                'djen-2026-06-01' AS p_item_ia
        """)
        path = tmp_path / "comunicacoes.parquet"
        con.execute(f"COPY comunicacoes TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD, {fragment})")
        con.close()
        result = validate_parquet(path, "comunicacoes")
        assert not result.passed
        assert any("unknown tribunals" in e for e in result.errors)

    def test_all_passed_helper(self) -> None:
        from causaganha.consolidate.validation import ValidationResult

        r1 = ValidationResult(table_name="a")
        r2 = ValidationResult(table_name="b", errors=["bad"])
        assert all_passed({"a": r1})
        assert not all_passed({"a": r1, "b": r2})
