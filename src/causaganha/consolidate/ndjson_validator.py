"""Phase 0.4: NDJSON input validation — check field coverage before transform.

Samples records from raw NDJSON files and verifies that the DJEN API
fields we depend on are present. If the API changes its field names and
>10% of records lack a critical field, the ZIP is rejected before any
Ibis transforms run.

Severity levels (shared with validation.py):
  BLOCK = do not transform, do not upload
  WARN  = log + transform proceeds, increment warning counter
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import structlog

from causaganha.consolidate.validation import ValidationResult
from causaganha.storage.djen_schema import (
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NUMERO_PROCESSO,
    FIELD_TIPO_COMUNICACAO,
)


if TYPE_CHECKING:
    from pathlib import Path


log = structlog.get_logger()

# Fields whose absence > threshold indicates the DJEN API changed shape.
# Each tuple lists all known naming variants for the same logical field.
_CRITICAL_FIELD_GROUPS: tuple[tuple[str, ...], ...] = (
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_NUMERO_PROCESSO,
    FIELD_TIPO_COMUNICACAO,
)

_MISSING_RATE_BLOCK = 0.10  # >10% → BLOCK


def validate_ndjson_sample(
    ndjson_dir: Path,
    *,
    sample_size: int = 200,
) -> ValidationResult:
    """Sample records from *.ndjson files and check critical field coverage.

    Reads up to sample_size lines across all *.ndjson files in ndjson_dir.
    For each critical field group, if >10% of sampled records have none of
    the known variants → BLOCK error (DJEN API schema changed).

    Returns a ValidationResult; table_name is set to "ndjson_input".
    """
    result = ValidationResult(table_name="ndjson_input")

    ndjson_files = sorted(ndjson_dir.glob("*.ndjson"))
    if not ndjson_files:
        result.warnings.append(f"No *.ndjson files found in {ndjson_dir}")
        return result

    records: list[dict] = _sample_records(ndjson_files, sample_size, result)
    if not records:
        result.errors.append("No valid NDJSON records found in sample")
        return result

    total = len(records)
    _check_field_coverage(records, total, result)

    log.info(
        "ndjson_sample_validated",
        records=total,
        files=len(ndjson_files),
        passed=result.passed,
    )
    return result


def _sample_records(
    ndjson_files: list,
    sample_size: int,
    result: ValidationResult,
) -> list[dict]:
    records: list[dict] = []
    for path in ndjson_files:
        if len(records) >= sample_size:
            break
        try:
            with path.open(encoding="utf-8") as f:
                for raw_line in f:
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    try:
                        records.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        continue
                    if len(records) >= sample_size:
                        break
        except OSError as e:
            result.warnings.append(f"Could not read {path.name}: {e}")
    return records


def _check_field_coverage(
    records: list[dict],
    total: int,
    result: ValidationResult,
) -> None:
    for field_group in _CRITICAL_FIELD_GROUPS:
        canonical = field_group[0]
        missing = sum(1 for rec in records if not any(v in rec for v in field_group))
        missing_rate = missing / total
        if missing_rate > _MISSING_RATE_BLOCK:
            result.errors.append(
                f"ndjson: field '{canonical}' missing in {missing}/{total} "
                f"sampled records ({missing_rate:.0%}) — DJEN API may have changed"
            )
