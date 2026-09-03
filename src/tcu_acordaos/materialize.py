"""Materialize the verified TCU Acórdãos product view as Parquet."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

import duckdb
import pandas as pd

from tcu_acordaos.ingest import AcquisitionProvenance, load_csv, transform_rows


PRODUCT_COLUMNS = (
    "key",
    "numero",
    "ano",
    "colegiado",
    "processo",
    "data_sessao",
    "relator",
    "situacao",
    "titulo",
    "assunto",
    "sumario",
    "acordao",
    "decisao",
    "relatorio",
    "voto",
    "source_url",
    "acquired_at",
    "source_sha256",
)


def materialize_parquet(
    csv_path: Path,
    destination: Path,
    *,
    source_url: str,
    acquired_at: str,
) -> int:
    """Write a queryable Parquet preserving official identity and provenance.

    The output intentionally contains only the loss-aware product fields from
    :mod:`tcu_acordaos.ingest`; in particular, ``VISAOGERAL`` never enters the
    authoritative TEOR artifact. The destination is replaced atomically only
    after DuckDB finishes writing a complete temporary Parquet.
    """
    if destination.suffix != ".parquet":
        msg = "TCU product artifact destination must end in .parquet"
        raise ValueError(msg)

    provenance = AcquisitionProvenance.from_file(
        csv_path,
        source_url=source_url,
        acquired_at=acquired_at,
    )
    records = transform_rows(load_csv(csv_path), provenance=provenance)
    frame = pd.DataFrame.from_records(
        (asdict(record) for record in records),
        columns=PRODUCT_COLUMNS,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.tmp")
    tmp_sql = str(tmp).replace("'", "''")
    con = duckdb.connect()
    try:
        con.register("tcu_records", frame)
        con.execute(
            "COPY (SELECT * FROM tcu_records ORDER BY ano, key) "
            f"TO '{tmp_sql}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        con.close()

    os.replace(tmp, destination)
    return len(records)
