#!/usr/bin/env python3
# Copyright 2026 CausaGanha. All rights reserved.
"""Render every web query contract against deterministic empty Parquet fixtures.

This helper is invoked by the frontend integration test.  It exercises the
real ``render_all`` registry without downloading production data and records
the query metadata needed to check frontend-contract coverage.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import duckdb


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.render_queries as renderer  # noqa: E402 — importado após o bootstrap de sys.path acima


def _write_relation(con: duckdb.DuckDBPyConnection, name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY (SELECT * FROM {name}) TO ? (FORMAT PARQUET)", [str(destination)])


def _write_fixtures(fixtures_dir: Path) -> Path:
    """Materialize a minimal typed Parquet input for every registered view."""
    con = duckdb.connect()
    try:
        renderer._synthetic_manifest(con)
        # A known row avoids NaN in totals.qmd while keeping the fixture stable
        # and representative of the manifest CSV/parquet input contract.
        con.execute(
            """INSERT INTO manifest VALUES
            ('TJRO', DATE '2099-01-01', 'uploaded', 'available', '200',
             '2026-01-01T00:00:00+00:00')"""
        )
        _write_relation(con, "manifest", fixtures_dir / "data" / "sync-manifest.parquet")

        renderer._synthetic_lawyer_ratings(con)
        _write_relation(
            con, "lawyer_ratings", fixtures_dir / "data/parquets/lawyer_ratings.parquet"
        )
        renderer._synthetic_ratings_history(con)
        _write_relation(
            con, "ratings_history", fixtures_dir / "data/parquets/ratings_history.parquet"
        )

        renderer._synthetic_acordaos(con)
        _write_relation(con, "acordaos", fixtures_dir / "data/stj/stj-acordaos.parquet")
        renderer._synthetic_tjro_juris(con)
        _write_relation(
            con, "tjro_juris", fixtures_dir / "data/tjro_juris/2026/tjro-juris-2026.parquet"
        )
        renderer._synthetic_datajud_capa(con)
        _write_relation(
            con, "datajud_capa", fixtures_dir / "data/datajud/datajud-capa-TJRO.parquet"
        )

        renderer._synthetic_comunicacoes(con)
        comunicacoes = fixtures_dir / "data/comunicacoes.parquet"
        _write_relation(con, "comunicacoes", comunicacoes)
    finally:
        con.close()
    return comunicacoes


def render_fixture(output_dir: Path) -> None:
    """Create fixtures, render into *output_dir*, and save query frontmatter."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    fixtures_dir = output_dir / "fixtures"
    comunicacoes = _write_fixtures(fixtures_dir)

    # The production registration functions derive their local input paths from
    # these module globals. Point them at our complete fixture tree instead.
    renderer.ROOT = fixtures_dir
    renderer.LOCAL_MANIFEST_PARQUET = fixtures_dir / "data/sync-manifest.parquet"
    renderer.DEV_RATINGS_DIR = fixtures_dir / "data/parquets"
    renderer._STJ_PARQUET = fixtures_dir / "data/stj/stj-acordaos.parquet"

    def register_comunicacoes(con: duckdb.DuckDBPyConnection) -> bool:
        renderer._register_view_from_parquet(con, "comunicacoes", comunicacoes)
        return True

    renderer._register_comunicacoes = register_comunicacoes
    public_dir = output_dir / "web/public"
    count, failures = renderer.render_all(public_dir=public_dir)
    if failures:
        raise RuntimeError("fixture rendering failed: " + "; ".join(failures))

    query_contracts = []
    for qmd in sorted(renderer.QUERIES_DIR.glob("*.qmd")):
        frontmatter, _ = renderer.parse_qmd(qmd)
        query_contracts.append(
            {
                "name": qmd.stem,
                "output": frontmatter["output"].lstrip("/"),
                "optional": frontmatter.get("optional", False),
            }
        )
    (output_dir / "query-contracts.json").write_text(
        json.dumps({"rendered_count": count, "contracts": query_contracts}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    render_fixture(args.output_dir)


if __name__ == "__main__":
    main()
