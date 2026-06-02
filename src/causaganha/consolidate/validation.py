"""Pragmatic Parquet validation — SQL asserts over DuckDB, zero extra deps.

Shared by both code paths:
  - src/causaganha/consolidate/exporter.py (refactored module)
  - scripts/pipeline/consolidate.py (legacy monolith used by CI workflow)

Severity levels:
  BLOCK = do not upload, do not mark checkpoint
  WARN  = log + upload proceeds, increment warning counter
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import duckdb
import structlog


if TYPE_CHECKING:
    from pathlib import Path

from causaganha.config import TRIBUNAIS
from causaganha.consolidate.schema_registry import (
    CURRENT_VERSION,
    SCHEMA_REGISTRY,
    _types_compatible,
)


log = structlog.get_logger()

KNOWN_TRIBUNALS: frozenset[str] = frozenset(TRIBUNAIS)

VALID_OUTCOMES: frozenset[str] = frozenset(
    {
        "WIN",
        "LOSS",
        "PARTIAL",
        "SETTLEMENT",
        "UNKNOWN",
    }
)


@dataclass
class ValidationResult:
    """Outcome of validating one Parquet table."""

    table_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True when no blocking errors were found."""
        return len(self.errors) == 0


def validate_parquet(
    path: Path,
    table_name: str,
    *,
    schema_version: str = CURRENT_VERSION,
    check_kv_metadata: bool = True,
) -> ValidationResult:
    """Validate a Parquet file against the declared schema.

    Returns a ValidationResult with errors (BLOCK) and warnings (WARN).
    """
    result = ValidationResult(table_name=table_name)

    if not path.exists():
        result.errors.append(f"File does not exist: {path}")
        return result

    schema_entry = SCHEMA_REGISTRY.get(schema_version)
    if schema_entry is None:
        result.errors.append(f"Unknown schema version: {schema_version}")
        return result

    expected_schema = schema_entry.tables.get(table_name)
    if expected_schema is None:
        result.errors.append(f"Table '{table_name}' not in schema {schema_version}")
        return result

    con = duckdb.connect()
    try:
        _validate_columns(con, path, table_name, expected_schema, result)
        if check_kv_metadata:
            _validate_kv_metadata(con, path, schema_version, result)
        _validate_row_count(con, path, table_name, result)
        _validate_invariants(con, path, table_name, result)
    except duckdb.Error as e:
        result.errors.append(f"DuckDB error reading {path}: {e}")
    finally:
        con.close()

    return result


def _validate_columns(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    table_name: str,
    expected_schema: object,
    result: ValidationResult,
) -> None:
    """Check column names and types match the expected schema."""
    cols = con.execute(f"DESCRIBE SELECT * FROM '{path}'").fetchall()
    actual_names = [c[0] for c in cols]
    actual_types = {c[0]: c[1] for c in cols}

    expected_pairs = list(expected_schema.items())
    expected_names = [name for name, _ in expected_pairs]
    expected_types = {name: str(dtype) for name, dtype in expected_pairs}

    missing = set(expected_names) - set(actual_names)
    if missing:
        result.errors.append(f"{table_name}: missing columns {sorted(missing)}")

    extra = set(actual_names) - set(expected_names)
    if extra:
        result.errors.append(f"{table_name}: unexpected extra columns {sorted(extra)}")

    for col_name in set(expected_names) & set(actual_names):
        expected_t = expected_types[col_name]
        actual_t = actual_types[col_name]
        if not _types_compatible(expected_t, actual_t):
            result.errors.append(
                f"{table_name}.{col_name}: expected type '{expected_t}', got '{actual_t}'"
            )


def _validate_kv_metadata(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    expected_version: str,
    result: ValidationResult,
) -> None:
    """Check that the Parquet footer contains the expected schema version stamp."""
    rows = con.execute(f"SELECT key, value FROM parquet_kv_metadata('{path}')").fetchall()
    kv = {
        (k.decode() if isinstance(k, bytes) else k): (v.decode() if isinstance(v, bytes) else v)
        for k, v in rows
    }
    actual = kv.get("causaganha.schema_version")
    if actual is None:
        result.errors.append("Missing causaganha.schema_version in Parquet KV metadata")
    elif actual != expected_version:
        result.errors.append(
            f"Schema version mismatch in KV metadata: expected '{expected_version}', got '{actual}'"
        )


def _validate_row_count(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    table_name: str,
    result: ValidationResult,
) -> None:
    """Warn on zero rows (empty date is possible but suspicious)."""
    row_count = con.execute(f"SELECT COUNT(*) FROM '{path}'").fetchone()[0]
    if row_count == 0:
        result.warnings.append(f"{table_name}: zero rows")


def _validate_invariants(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    table_name: str,
    result: ValidationResult,
) -> None:
    """Check domain-specific invariants per table."""
    if table_name == "comunicacoes":
        _check_not_null(con, path, "id", table_name, result)
        _check_tribunal_domain(con, path, "tribunal", table_name, result)

    elif table_name == "textos":
        _check_not_null(con, path, "id", table_name, result)
        empty = con.execute(
            f"SELECT COUNT(*) FROM '{path}' WHERE texto IS NULL OR texto = ''"
        ).fetchone()[0]
        if empty > 0:
            result.errors.append(f"textos: {empty} rows with NULL/empty texto")

    elif table_name == "advogados":
        _check_not_null(con, path, "id", table_name, result)

    elif table_name == "classificacoes":
        _check_not_null(con, path, "outcome", table_name, result)
        _check_not_null(con, path, "confidence", table_name, result)

        invalid_outcomes = con.execute(
            f"SELECT DISTINCT outcome FROM '{path}' "
            f"WHERE outcome IS NOT NULL "
            f"AND outcome NOT IN ({','.join(repr(o) for o in VALID_OUTCOMES)})"
        ).fetchall()
        if invalid_outcomes:
            vals = [r[0] for r in invalid_outcomes]
            result.errors.append(f"classificacoes: invalid outcomes {vals}")

        bad_confidence = con.execute(
            f"SELECT COUNT(*) FROM '{path}' "
            f"WHERE confidence IS NOT NULL AND (confidence < 0 OR confidence > 1)"
        ).fetchone()[0]
        if bad_confidence > 0:
            result.errors.append(
                f"classificacoes: {bad_confidence} rows with confidence outside [0,1]"
            )

    elif table_name in ("destinatarios", "comunicacao_advogados", "representacoes"):
        _check_not_null(con, path, "comunicacao_id", table_name, result)

    elif table_name == "processos":
        _check_not_null(con, path, "numero_processo", table_name, result)
        _check_tribunal_domain(con, path, "tribunal", table_name, result)


def _check_not_null(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    column: str,
    table_name: str,
    result: ValidationResult,
) -> None:
    null_count = con.execute(
        f"SELECT COUNT(*) FROM '{path}' WHERE \"{column}\" IS NULL"
    ).fetchone()[0]
    if null_count > 0:
        result.errors.append(f"{table_name}: {null_count} NULL values in '{column}'")


def _check_tribunal_domain(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    column: str,
    table_name: str,
    result: ValidationResult,
) -> None:
    tribunals = con.execute(
        f'SELECT DISTINCT "{column}" FROM \'{path}\' WHERE "{column}" IS NOT NULL'
    ).fetchall()
    unknown = [r[0] for r in tribunals if r[0] not in KNOWN_TRIBUNALS]
    if unknown:
        result.errors.append(f"{table_name}: unknown tribunal codes in '{column}': {unknown[:5]}")


def all_passed(results: dict[str, ValidationResult]) -> bool:
    """True when every table in the results dict passed validation."""
    return all(r.passed for r in results.values())


def validate_all_tables(
    output_dir: Path,
    *,
    schema_version: str = CURRENT_VERSION,
    check_kv_metadata: bool = True,
) -> dict[str, ValidationResult]:
    """Validate all Parquet files in a directory against the schema.

    Returns a dict of table_name → ValidationResult.
    Use ``all_passed(results)`` to gate the completion marker.
    """
    schema_entry = SCHEMA_REGISTRY.get(schema_version)
    if schema_entry is None:
        return {}

    results: dict[str, ValidationResult] = {}
    for table_name in schema_entry.tables:
        parquet_path = output_dir / f"{table_name}.parquet"
        if parquet_path.exists():
            r = validate_parquet(
                parquet_path,
                table_name,
                schema_version=schema_version,
                check_kv_metadata=check_kv_metadata,
            )
            results[table_name] = r
            if r.errors:
                log.error("validation_failed", table=table_name, errors=r.errors)
            if r.warnings:
                log.warning("validation_warnings", table=table_name, warnings=r.warnings)

    return results
