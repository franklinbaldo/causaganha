"""Schema registry: versioned, immutable table schemas for consolidated Parquets.

Three-layer versioning (inspired by ficha ADR 0003):
  1. KV metadata embedded in Parquet footer (causaganha.schema_version)
  2. This Python registry (ETL side) — maps version → table schemas
  3. Zod schemas in web/src/schemas/vN/ (frontend side, future)

Rules:
  - Never edit a published schema. Changes → new version.
  - SemVer: patch = optional field added, minor = required field with default,
    major = field removed/renamed/type changed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import ibis


IBIS_TO_DUCKDB_TYPES: dict[str, set[str]] = {
    "string": {"VARCHAR", "TEXT", "STRING"},
    "int32": {"INTEGER", "INT4", "INT32", "INT", "SIGNED"},
    "int64": {"BIGINT", "INT8", "INT64", "LONG", "HUGEINT"},
    "float64": {"DOUBLE", "FLOAT8", "NUMERIC", "DECIMAL"},
    "date": {"DATE"},
    "timestamp": {"TIMESTAMP", "DATETIME", "TIMESTAMP WITH TIME ZONE"},
    "boolean": {"BOOLEAN", "BOOL", "LOGICAL"},
}


def _types_compatible(ibis_type: str, duckdb_type: str) -> bool:
    """Check if a DuckDB column type is compatible with an Ibis schema type."""
    duckdb_upper = duckdb_type.upper().strip()
    allowed = IBIS_TO_DUCKDB_TYPES.get(ibis_type)
    if allowed is None:
        return ibis_type.upper() in duckdb_upper
    return duckdb_upper in allowed


@dataclass(frozen=True)
class SchemaVersion:
    """Immutable snapshot of all table schemas for a given version."""

    version: str
    tables: dict[str, ibis.Schema]
    created_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def get_table_schema(self, table_name: str) -> ibis.Schema:
        """Look up a table's schema. Raises KeyError if not found."""
        if table_name not in self.tables:
            msg = f"Table '{table_name}' not in schema version {self.version}"
            raise KeyError(msg)
        return self.tables[table_name]


SCHEMA_V3 = SchemaVersion(
    version="3.0.0",
    created_at="2026-05-01",
    tables={
        "comunicacoes": ibis.schema(
            {
                "id": "string",
                "original_id": "string",
                "tribunal": "string",
                "numero_processo": "string",
                "numero_processo_mascara": "string",
                "data_disponibilizacao": "date",
                "tipo_comunicacao": "string",
                "nome_orgao": "string",
                "meio": "string",
                "link": "string",
                "tipo_documento": "string",
                "nome_classe": "string",
                "codigo_classe": "string",
                "numero_comunicacao": "string",
                "hash": "string",
                "processed_at": "timestamp",
                "texto_id": "string",
                "p_ano": "int32",
                "p_mes": "int32",
                "p_item_ia": "string",
            },
        ),
        "advogados": ibis.schema(
            {
                "id": "string",
                "original_id": "string",
                "tribunal": "string",
                "nome": "string",
                "numero_oab": "string",
                "uf_oab": "string",
                "p_ano": "int32",
                "p_mes": "int32",
                "p_item_ia": "string",
            },
        ),
        "advogado_nomes": ibis.schema(
            {
                "advogado_id": "string",
                "nome": "string",
                "tribunal": "string",
                "first_seen": "date",
            },
        ),
        "destinatarios": ibis.schema(
            {
                "comunicacao_id": "string",
                "tribunal": "string",
                "nome": "string",
                "polo": "string",
                "parte_id": "string",
                "p_ano": "int32",
                "p_mes": "int32",
                "p_item_ia": "string",
            },
        ),
        "comunicacao_advogados": ibis.schema(
            {
                "comunicacao_id": "string",
                "tribunal": "string",
                "advogado_id": "string",
            },
        ),
        "textos": ibis.schema(
            {
                "id": "string",
                "texto": "string",
            },
        ),
        "representacoes": ibis.schema(
            {
                "comunicacao_id": "string",
                "tribunal": "string",
                "advogado_id": "string",
                "parte_id": "string",
                "polo": "string",
                "p_ano": "int32",
                "p_mes": "int32",
                "p_item_ia": "string",
            },
        ),
        "processos": ibis.schema(
            {
                "numero_processo": "string",
                "tribunal": "string",
                "data": "date",
                "comunicacao_id": "string",
                "p_ano": "int32",
                "p_mes": "int32",
                "p_item_ia": "string",
            },
        ),
        "partes": ibis.schema(
            {
                "id": "string",
                "nome_normalizado": "string",
                "nome_original": "string",
            },
        ),
    },
)

CURRENT_VERSION = "3.0.0"

# Incremented whenever the physical layout of exported Parquets changes
# (ORDER BY keys, ROW_GROUP_SIZE, bloom-filter flags) without touching the
# logical schema.  Items whose manifest carries an older revision are
# reconsolidated automatically by `reconsolidate` without a schema bump.
# Bump this string when rolling out new layout settings.
CURRENT_LAYOUT_REVISION = "1"

# ── SCHEMA_V4 (parked — NOT active) ──────────────────────────────────────────
# Gated on A0e measurement: only activate when encoding_comparison.py confirms
# that UUID→blob + CNJ→DECIMAL(20,0) savings justify a major re-upload.
#
# Changes vs v3:
#   - Internally-generated UUID columns (id, texto_id, comunicacao_id,
#     advogado_id, parte_id): "string" → "binary" (16-byte raw UUID).
#   - original_id: STAYS "string" — comes from external DJEN source; format is
#     not guaranteed to be a valid UUID (could be an arbitrary identifier).
#     Binary conversion would silently corrupt non-conforming values with no
#     recovery path. Keep as string until a full audit of the source data
#     confirms 100% UUID conformance.
#   - numero_processo: "string" → "decimal(20, 0)" (FIXED_LEN_BYTE_ARRAY, ~16 B)
#     ⚠ DECIMAL loses leading zeros — consumers MUST LPAD(val::VARCHAR, 20, '0')
#   - hash: "string" → "binary" (raw SHA-256 bytes)
#   - p_item_ia removed (info lives in KV_METADATA footer + IA path)
#     ⚠ Audit frontend/scripts for p_item_ia usage before activating
#
# To activate: set CURRENT_VERSION = "4.0.0" and run reconsolidate --force.
# Prerequisite: run scripts/snapshot_parquets_for_rollback.py first (A-pré).
SCHEMA_V4 = SchemaVersion(
    version="4.0.0",
    created_at="2026-06-07",
    tables={
        "comunicacoes": ibis.schema(
            {
                "id": "binary",
                "original_id": "string",  # external source — not guaranteed UUID
                "tribunal": "string",
                "numero_processo": "decimal(20, 0)",
                "numero_processo_mascara": "string",
                "data_disponibilizacao": "date",
                "tipo_comunicacao": "string",
                "nome_orgao": "string",
                "meio": "string",
                "link": "string",
                "tipo_documento": "string",
                "nome_classe": "string",
                "codigo_classe": "string",
                "numero_comunicacao": "string",
                "hash": "binary",
                "processed_at": "timestamp",
                "texto_id": "binary",
                "p_ano": "int32",
                "p_mes": "int32",
            },
        ),
        "advogados": ibis.schema(
            {
                "id": "binary",
                "original_id": "string",  # external source — not guaranteed UUID
                "tribunal": "string",
                "nome": "string",
                "numero_oab": "string",
                "uf_oab": "string",
                "p_ano": "int32",
                "p_mes": "int32",
            },
        ),
        "advogado_nomes": ibis.schema(
            {
                "advogado_id": "binary",
                "nome": "string",
                "tribunal": "string",
                "first_seen": "date",
            },
        ),
        "destinatarios": ibis.schema(
            {
                "comunicacao_id": "binary",
                "tribunal": "string",
                "nome": "string",
                "polo": "string",
                "parte_id": "binary",
                "p_ano": "int32",
                "p_mes": "int32",
            },
        ),
        "comunicacao_advogados": ibis.schema(
            {
                "comunicacao_id": "binary",
                "tribunal": "string",
                "advogado_id": "binary",
            },
        ),
        "textos": ibis.schema(
            {
                "id": "binary",
                "texto": "string",
            },
        ),
        "representacoes": ibis.schema(
            {
                "comunicacao_id": "binary",
                "tribunal": "string",
                "advogado_id": "binary",
                "parte_id": "binary",
                "polo": "string",
                "p_ano": "int32",
                "p_mes": "int32",
            },
        ),
        "processos": ibis.schema(
            {
                "numero_processo": "decimal(20, 0)",
                "tribunal": "string",
                "data": "date",
                "comunicacao_id": "binary",
                "p_ano": "int32",
                "p_mes": "int32",
            },
        ),
        "partes": ibis.schema(
            {
                "id": "binary",
                "nome_normalizado": "string",
                "nome_original": "string",
            },
        ),
    },
)

SCHEMA_REGISTRY: dict[str, SchemaVersion] = {
    "3.0.0": SCHEMA_V3,
    # "4.0.0": SCHEMA_V4,  # Activate after A0e confirms savings + A-pré snapshot taken
}


def get_schema(version: str) -> SchemaVersion:
    """Look up a schema version. Raises KeyError if not found."""
    if version not in SCHEMA_REGISTRY:
        msg = f"Schema version '{version}' not found. Available: {list(SCHEMA_REGISTRY.keys())}"
        raise KeyError(msg)
    return SCHEMA_REGISTRY[version]


def get_current_schema() -> SchemaVersion:
    """Return the current (latest) schema version."""
    return SCHEMA_REGISTRY[CURRENT_VERSION]


def kv_metadata_for_export(item_id: str) -> dict[str, str]:
    """Return KV metadata dict to embed in Parquet footer via DuckDB."""
    return {
        "causaganha.schema_version": CURRENT_VERSION,
        "causaganha.item_id": item_id,
    }


def kv_metadata_sql_fragment(item_id: str) -> str:
    """Return the KV_METADATA clause for a DuckDB COPY statement."""
    meta = kv_metadata_for_export(item_id)
    pairs = ", ".join(f"'{k}': '{v}'" for k, v in meta.items())
    return f"KV_METADATA {{{pairs}}}"
