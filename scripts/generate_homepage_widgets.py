#!/usr/bin/env python3
"""Generate homepage widget data from consolidated Parquet lake on Internet Archive.

Reads `manifest.parquet` from the causaganha-catalog to discover the remote URLs
of all `*-comunicacoes.parquet` and `*-advogados.parquet` files, then aggregates
three widgets:

  1. activity_summary: counts for the last closed month (intimations, unique OABs,
     processes, tribunals active).
  2. top_tribunais_30d: top 5 tribunals by volume of communications in the last
     30 days.
  3. top_advogados_atividade: top 20 lawyers by case count in the current year
     (nominal, descriptive — NOT a quality ranking).

The output JSON is read at Astro build time by `web/src/pages/index.astro` via
`readJson('cache/homepage-widgets.json')`. If any widget fails to build, we emit
an empty list/dict for that key and let the Astro page render gracefully.

Usage:
    python scripts/generate_homepage_widgets.py
        [--output web/public/cache/homepage-widgets.json]
        [--year 2026]
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb


logger = logging.getLogger("generate_homepage_widgets")

SCHEMA_VERSION = 1
MANIFEST_URL = "https://archive.org/download/causaganha-catalog/manifest.parquet"
TOP_TRIBUNAIS_LIMIT = 5
TOP_ADVOGADOS_LIMIT = 20
MIN_CASES_PER_LAWYER = 10


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    return con


def _load_manifest(con: duckdb.DuckDBPyConnection) -> bool:
    """Load the global manifest. Returns False if it can't be loaded."""
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE manifest AS SELECT * FROM read_parquet('{MANIFEST_URL}')"
        )
        row = con.execute("SELECT COUNT(*) FROM manifest").fetchone()
        if row is None or row[0] == 0:
            logger.warning("manifest is empty")
            return False
        logger.info("manifest loaded: %s rows", row[0])
    except duckdb.Error as exc:
        logger.warning("failed to load manifest: %s", exc)
        return False
    return True


def _discover_parquet_urls(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    year: int | None = None,
) -> list[str]:
    """Find all Parquet URLs for a given table (e.g. 'comunicacoes' or 'advogados').

    The manifest schema varies slightly between codepaths; we try the most common
    columns and fall back gracefully. Filters by year on the `date` column when
    provided.
    """
    year_filter = f"AND date LIKE '{year}-%'" if year is not None else ""
    candidate_sqls = [
        f"""
        SELECT DISTINCT ia_url
        FROM manifest
        WHERE file_type = 'parquet'
          AND table_name = '{table_name}'
          {year_filter}
        """,
        f"""
        SELECT DISTINCT ia_url
        FROM manifest
        WHERE file_name LIKE '%-{table_name}.parquet'
          {year_filter}
        """,
    ]
    for sql in candidate_sqls:
        try:
            rows = con.execute(sql).fetchall()
        except duckdb.Error as exc:
            logger.debug("manifest probe failed for %s: %s", table_name, exc)
            continue
        urls = [r[0] for r in rows if r and r[0]]
        if urls:
            logger.info("discovered %d %s parquets", len(urls), table_name)
            return urls
    logger.warning("no %s parquets discovered", table_name)
    return []


def _array_literal(urls: list[str]) -> str:
    """Render a DuckDB array literal of strings from a Python list.

    We validate that every URL looks like an IA archive URL to reduce the risk of
    SQL injection through poisoned manifest rows.
    """
    clean = []
    for url in urls:
        if not isinstance(url, str):
            continue
        if not url.startswith("https://archive.org/"):
            continue
        if "'" in url or ";" in url or "--" in url:
            continue
        clean.append(f"'{url}'")
    return "[" + ", ".join(clean) + "]"


def _activity_summary(
    con: duckdb.DuckDBPyConnection,
    com_urls: list[str],
    adv_urls: list[str],
    year: int,
) -> dict[str, Any]:
    """Widget 1: last closed month summary (intimations, OABs, processes, tribunals)."""
    if not com_urls or not adv_urls:
        return {}
    # Last closed month = previous calendar month relative to today (UTC).
    now = datetime.now(UTC)
    if now.month == 1:
        period_year, period_month = now.year - 1, 12
    else:
        period_year, period_month = now.year, now.month - 1
    try:
        row = con.execute(
            f"""
            WITH com AS (
                SELECT intimation_id, sigla_tribunal, numero_processo
                FROM read_parquet({_array_literal(com_urls)}, union_by_name=true)
                WHERE year = {period_year} AND month = {period_month}
            ),
            adv AS (
                SELECT intimation_id, oab_number, oab_state
                FROM read_parquet({_array_literal(adv_urls)}, union_by_name=true)
                WHERE oab_number IS NOT NULL AND oab_state IS NOT NULL
            )
            SELECT
                COUNT(DISTINCT com.intimation_id) AS intimacoes,
                COUNT(DISTINCT adv.oab_number || '/' || adv.oab_state) AS oabs,
                COUNT(DISTINCT com.numero_processo) AS processos,
                COUNT(DISTINCT com.sigla_tribunal) AS tribunais
            FROM com LEFT JOIN adv USING(intimation_id)
            """
        ).fetchone()
    except duckdb.Error as exc:
        logger.warning("activity_summary failed: %s", exc)
        return {}
    if row is None:
        return {}
    intimacoes, oabs, processos, tribunais = row
    if not intimacoes:
        return {}
    return {
        "periodo": f"{period_year:04d}-{period_month:02d}",
        "intimacoes": int(intimacoes),
        "oabs_unicas": int(oabs or 0),
        "processos": int(processos or 0),
        "tribunais": int(tribunais or 0),
    }


def _top_tribunais_30d(
    con: duckdb.DuckDBPyConnection,
    com_urls: list[str],
) -> list[dict[str, Any]]:
    """Widget 2: top tribunals by communications volume in the last 30 days."""
    if not com_urls:
        return []
    try:
        rows = con.execute(
            f"""
            SELECT sigla_tribunal AS tribunal, COUNT(*) AS comunicacoes
            FROM read_parquet({_array_literal(com_urls)}, union_by_name=true)
            WHERE data_disponibilizacao >= current_date - INTERVAL 30 DAY
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT {TOP_TRIBUNAIS_LIMIT}
            """
        ).fetchall()
    except duckdb.Error as exc:
        logger.warning("top_tribunais_30d failed: %s", exc)
        return []
    return [{"tribunal": r[0], "comunicacoes": int(r[1])} for r in rows if r and r[0]]


def _top_advogados_atividade(
    con: duckdb.DuckDBPyConnection,
    com_urls: list[str],
    adv_urls: list[str],
    year: int,
) -> list[dict[str, Any]]:
    """Widget 3: top lawyers by volume of communications in the given year.

    Filters out singletons (< MIN_CASES_PER_LAWYER) to keep signal/noise high.
    Includes per-lawyer primary tribunal and autor/réu split.
    """
    if not com_urls or not adv_urls:
        return []
    try:
        rows = con.execute(
            f"""
            WITH com AS (
                SELECT intimation_id, sigla_tribunal
                FROM read_parquet({_array_literal(com_urls)}, union_by_name=true)
                WHERE year = {year}
            ),
            adv AS (
                SELECT intimation_id, oab_number, oab_state, lawyer_name, polo
                FROM read_parquet({_array_literal(adv_urls)}, union_by_name=true)
                WHERE oab_number IS NOT NULL AND oab_state IS NOT NULL
            ),
            joined AS (
                SELECT com.intimation_id, com.sigla_tribunal,
                       adv.oab_number, adv.oab_state, adv.lawyer_name, adv.polo
                FROM com JOIN adv USING(intimation_id)
            ),
            per_lawyer_tribunal AS (
                SELECT oab_number, oab_state, sigla_tribunal, COUNT(*) AS n
                FROM joined GROUP BY 1, 2, 3
            ),
            primary_tribunal AS (
                SELECT oab_number, oab_state, sigla_tribunal AS tribunal_principal
                FROM (
                    SELECT oab_number, oab_state, sigla_tribunal,
                           ROW_NUMBER() OVER (PARTITION BY oab_number, oab_state
                                              ORDER BY n DESC, sigla_tribunal) AS rk
                    FROM per_lawyer_tribunal
                )
                WHERE rk = 1
            ),
            totals AS (
                SELECT oab_number, oab_state,
                       any_value(lawyer_name) AS nome,
                       COUNT(*) AS comunicacoes,
                       AVG(CASE WHEN polo = 'A' THEN 1.0
                                WHEN polo = 'P' THEN 0.0 END) AS pct_autor
                FROM joined
                GROUP BY 1, 2
                HAVING COUNT(*) >= {MIN_CASES_PER_LAWYER}
            )
            SELECT t.oab_number, t.oab_state, t.nome,
                   t.comunicacoes, p.tribunal_principal, t.pct_autor
            FROM totals t JOIN primary_tribunal p USING(oab_number, oab_state)
            ORDER BY t.comunicacoes DESC, t.oab_number
            LIMIT {TOP_ADVOGADOS_LIMIT}
            """
        ).fetchall()
    except duckdb.Error as exc:
        logger.warning("top_advogados_atividade failed: %s", exc)
        return []

    results: list[dict[str, Any]] = []
    for row in rows:
        oab, uf, nome, n, trib, pct_autor = row
        # pct_autor may be NULL if polo is always other values; clamp to [0,1].
        if pct_autor is None:
            autor_pct = 0.0
        else:
            autor_pct = max(0.0, min(1.0, float(pct_autor)))
        results.append(
            {
                "oab": oab,
                "uf": uf,
                "nome": nome,
                "comunicacoes": int(n),
                "tribunal_principal": trib,
                "polos": {
                    "A": round(autor_pct, 3),
                    "P": round(1.0 - autor_pct, 3),
                },
            }
        )
    return results


def build_widgets(year: int) -> dict[str, Any]:
    """Build the full homepage-widgets payload.

    Always returns a valid envelope. Individual widgets may be empty if their
    underlying data isn't available yet.
    """
    con = _connect()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "year": year,
        "activity_summary": {},
        "top_tribunais_30d": [],
        "top_advogados_atividade": [],
    }

    if not _load_manifest(con):
        return payload

    com_urls = _discover_parquet_urls(con, "comunicacoes", year=year)
    adv_urls = _discover_parquet_urls(con, "advogados", year=year)

    payload["activity_summary"] = _activity_summary(con, com_urls, adv_urls, year)
    payload["top_tribunais_30d"] = _top_tribunais_30d(con, com_urls)
    payload["top_advogados_atividade"] = _top_advogados_atividade(con, com_urls, adv_urls, year)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="web/public/cache/homepage-widgets.json",
        help="Output path for the widget JSON",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now(UTC).year,
        help="Year to aggregate over for the 'top advogados' widget",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    payload = build_widgets(args.year)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    summary = payload.get("activity_summary") or {}
    logger.info(
        "wrote %s (year=%s, periodo=%s, intimacoes=%s, top_tribunais=%d, top_advogados=%d)",
        output_path,
        args.year,
        summary.get("periodo", "n/a"),
        summary.get("intimacoes", "n/a"),
        len(payload["top_tribunais_30d"]),
        len(payload["top_advogados_atividade"]),
    )


if __name__ == "__main__":
    main()
