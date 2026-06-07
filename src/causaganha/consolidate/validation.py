"""Pragmatic Parquet validation — SQL asserts over DuckDB, zero extra deps.

Shared by both code paths:
  - src/causaganha/consolidate/exporter.py (refactored module)
  - scripts/pipeline/consolidate.py (legacy monolith used by CI workflow)

Severity levels:
  BLOCK = do not upload, do not mark checkpoint
  WARN  = log + upload proceeds, increment warning counter
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb
import ibis
import structlog

from causaganha.config import TRIBUNAIS
from causaganha.consolidate.schema_registry import (
    CURRENT_VERSION,
    SCHEMA_REGISTRY,
    _types_compatible,
    get_current_schema,
)


log = structlog.get_logger()

KNOWN_TRIBUNALS: frozenset[str] = frozenset(t.upper() for t in TRIBUNAIS)

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
    unknown = [r[0] for r in tribunals if r[0].upper() not in KNOWN_TRIBUNALS]
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


MIN_DATE_LENGTH = 10


def validate_parquet_schema(file_path: Path, table_name: str) -> None:
    """Validate that the Parquet file's columns and types match the expected schema using Ibis."""
    con = ibis.duckdb.connect()
    table = con.read_parquet(file_path)
    actual_schema = table.schema()
    expected_schema = get_current_schema().tables[table_name]

    actual_names = set(actual_schema.names)
    expected_names = set(expected_schema.names)

    if actual_names != expected_names:
        missing = expected_names - actual_names
        extra = actual_names - expected_names
        msg = (
            f"Schema column mismatch in {file_path} for table '{table_name}'. "
            f"Missing: {missing}, Extra: {extra}"
        )
        raise ValueError(msg)

    # Validate types compatibility
    for name, expected_type in expected_schema.items():
        actual_type = actual_schema[name]
        expected_type_str = str(expected_type)
        actual_type_str = str(actual_type)

        actual_norm = actual_type_str.lower()
        if "string" in actual_norm:
            actual_base = "string"
        elif "int32" in actual_norm:
            actual_base = "int32"
        elif "int64" in actual_norm:
            actual_base = "int64"
        elif "date" in actual_norm:
            actual_base = "date"
        elif "timestamp" in actual_norm:
            actual_base = "timestamp"
        elif "float64" in actual_norm or "double" in actual_norm or "float" in actual_norm:
            actual_base = "float64"
        else:
            actual_base = actual_norm

        if actual_base != expected_type_str:
            msg = (
                f"Column '{name}' in {file_path} expected "
                f"{expected_type_str}, got {actual_type_str}"
            )
            raise ValueError(msg)

    log.info("parquet_schema_validated", file=str(file_path), table=table_name)


def validate_ndjson_record(record: dict[str, Any]) -> bool:
    """Validate a raw DJEN record before writing to NDJSON.

    Checks that the record:
      - Is a dictionary.
      - Has a non-empty string or integer 'id'.
      - Has a non-empty date field under one of the observed variants.
    """
    if not isinstance(record, dict):
        return False

    rec_id = record.get("id")
    if rec_id is None or str(rec_id).strip() == "":
        return False

    has_date = False
    for variant in (
        "data_disponibilizacao",
        "datadisponibilizacao",
        "dataDisponibilizacao",
    ):
        val = record.get(variant)
        if val is not None and str(val).strip() != "":
            val_str = str(val).strip()
            if len(val_str) >= MIN_DATE_LENGTH:
                has_date = True
                break
    return has_date


def _read_raw_records(raw_ndjson_dir: Path) -> list[dict[str, Any]]:
    """Read all validated raw records from NDJSON files."""
    raw_records = []
    for ndjson_file in raw_ndjson_dir.glob("*.ndjson"):
        with ndjson_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    if validate_ndjson_record(rec):
                        raw_records.append(rec)
                except json.JSONDecodeError:
                    continue
    return raw_records


def _verify_sample_equivalence(
    raw_records: list[dict[str, Any]],
    original_ids: list[str],
    texto_ids: list[str],
    txt_map: dict[str, str],
) -> None:
    """Verify sample of raw records match Parquet rows."""
    id_to_index = {str(orig_id): idx for idx, orig_id in enumerate(original_ids)}
    sample_records = raw_records[:50]
    for rec in sample_records:
        rec_id = str(rec["id"])
        if rec_id not in id_to_index:
            msg = f"Roundtrip equivalence failed: Original ID '{rec_id}' not found in Parquet"
            raise ValueError(msg)

        idx = id_to_index[rec_id]
        rec_text = rec.get("texto", "")
        if rec_text and txt_map:
            texto_id = texto_ids[idx]
            if not texto_id:
                msg = (
                    f"Roundtrip equivalence failed: original_id '{rec_id}' "
                    "has empty texto_id in Parquet"
                )
                raise ValueError(msg)

            if texto_id not in txt_map:
                msg = (
                    f"Roundtrip equivalence failed: texto_id '{texto_id}' "
                    "not found in textos Parquet"
                )
                raise ValueError(msg)

            pq_text = txt_map[texto_id]
            if pq_text != rec_text:
                msg = (
                    f"Roundtrip equivalence failed: Text mismatch for original_id '{rec_id}'. "
                    f"Expected: {rec_text[:50]!r}, Got: {pq_text[:50]!r}"
                )
                raise ValueError(msg)


def validate_roundtrip_equivalence(raw_ndjson_dir: Path, parquet_dir: Path) -> None:
    """Verify that exported Parquet tables can reconstruct the source NDJSON data.

    Performs the following assertions:
      1. Row count of 'comunicacoes' table must match the total number of validated NDJSON records.
      2. For a sample of records from the NDJSON, verifies:
         - The record ID is present in the 'comunicacoes' Parquet.
         - The text (if present) matches the text in the 'textos' Parquet.
    """
    raw_records = _read_raw_records(raw_ndjson_dir)
    if not raw_records:
        log.warning("roundtrip_validation_no_records")
        return

    comunicacoes_path = parquet_dir / "comunicacoes.parquet"
    textos_path = parquet_dir / "textos.parquet"

    if not comunicacoes_path.exists():
        msg = f"Missing expected Parquet file: {comunicacoes_path}"
        raise FileNotFoundError(msg)

    con = ibis.duckdb.connect()
    com_table = con.read_parquet(comunicacoes_path)
    original_ids = com_table["original_id"].execute().tolist()
    texto_ids = com_table["texto_id"].execute().tolist()

    if len(original_ids) != len(raw_records):
        msg = (
            f"Roundtrip equivalence row count mismatch: NDJSON has {len(raw_records)} "
            f"records, but comunicacoes Parquet has {len(original_ids)} rows"
        )
        raise ValueError(msg)

    txt_map = {}
    if textos_path.exists():
        txt_table = con.read_parquet(textos_path)
        txt_ids = txt_table["id"].execute().tolist()
        txt_texts = txt_table["texto"].execute().tolist()
        txt_map = dict(zip(txt_ids, txt_texts, strict=True))

    _verify_sample_equivalence(raw_records, original_ids, texto_ids, txt_map)
    log.info(
        "roundtrip_equivalence_validated",
        checked_records=len(raw_records[:50]),
        total_records=len(raw_records),
    )


def update_consolidation_manifest(
    target_key: str, stats: dict[str, Any], *, is_date: bool = True
) -> None:
    """Update or append consolidation metrics for target_key to data/consolidation-manifest.json."""
    manifest_path = Path("data/consolidation-manifest.json")

    data: dict[str, Any] = {"schema_version": CURRENT_VERSION, "dates": {}}
    if manifest_path.exists():
        try:
            with manifest_path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    data["dates"] = loaded.get("dates", {})
        except (OSError, json.JSONDecodeError) as e:
            log.warning("failed_to_load_consolidation_manifest", error=str(e))

    item_id = f"djen-{target_key}" if is_date else f"djen-{target_key.lower()}"

    data["dates"][target_key] = {
        "item_id": item_id,
        "zips_processed": stats.get("zips_processed", 0),
        "records_count": stats.get("records", 0),
        "parquets_created": stats.get("parquets_created", 0),
        "uploaded_mb": round(stats.get("uploaded_mb", 0.0), 3),
        "consolidated_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log.info(
        "consolidation_manifest_updated",
        path=str(manifest_path),
        date=target_key,
    )
