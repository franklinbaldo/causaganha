"""Minimal, source-faithful ingestion helpers for TCU acórdãos."""

from .ingest import (
    REQUIRED_COLUMNS,
    AcordaoRecord,
    AcquisitionProvenance,
    canonical_key,
    load_csv,
    search_teor,
    transform_rows,
)

__all__ = [
    "REQUIRED_COLUMNS",
    "AcordaoRecord",
    "AcquisitionProvenance",
    "canonical_key",
    "load_csv",
    "search_teor",
    "transform_rows",
]
