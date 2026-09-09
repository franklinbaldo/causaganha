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


def _write_fixtures(fixtures_dir: Path) -> dict[str, Path]:
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
        tjro_juris = fixtures_dir / "data/tjro_juris/2026/tjro-juris-2026.parquet"
        _write_relation(con, "tjro_juris", tjro_juris)
        renderer._synthetic_datajud_capa(con)
        datajud_capa = fixtures_dir / "data/datajud/datajud-capa-TJRO.parquet"
        _write_relation(con, "datajud_capa", datajud_capa)

        renderer._synthetic_comunicacoes(con)
        comunicacoes = fixtures_dir / "data/comunicacoes.parquet"
        _write_relation(con, "comunicacoes", comunicacoes)
    finally:
        con.close()
    return {
        "comunicacoes": comunicacoes,
        "tjro_juris": tjro_juris,
        "datajud_capa": datajud_capa,
    }


def render_fixture(output_dir: Path) -> None:
    """Create fixtures, render into *output_dir*, and save query frontmatter."""
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    fixtures_dir = output_dir / "fixtures"
    fixture_paths = _write_fixtures(fixtures_dir)

    # The production registration functions derive their local input paths from
    # these module globals. Point them at our complete fixture tree instead.
    renderer.ROOT = fixtures_dir
    renderer.LOCAL_MANIFEST_PARQUET = fixtures_dir / "data/sync-manifest.parquet"
    renderer.DEV_RATINGS_DIR = fixtures_dir / "data/parquets"
    renderer._STJ_PARQUET = fixtures_dir / "data/stj/stj-acordaos.parquet"

    def register_comunicacoes(con: duckdb.DuckDBPyConnection) -> bool:
        renderer._register_view_from_parquet(con, "comunicacoes", fixture_paths["comunicacoes"])
        return True

    renderer._register_comunicacoes = register_comunicacoes

    # _register_tjro_juris/_register_datajud_capa (fixed to fall back to IA via
    # reconcile_processos.ensure_juris_parquets()/ensure_datajud_parquets() —
    # see this round's AgentDecision) read their local-file paths from
    # reconcile_processos's own ROOT/DATA_DIR module globals, not renderer.ROOT
    # above — so without this they'd see no local files here and hit the real
    # network for IA fallback, exactly like tests/test_render_queries.py mocks
    # the same two functions directly to avoid that.
    reconcile_processos = renderer.reconcile_processos

    def fake_ensure_juris_parquets():
        path = fixture_paths["tjro_juris"]
        urls = {path: f"https://archive.org/download/{path.stem}/{path.name}"}
        load = reconcile_processos.SourceLoad(
            "juris", reconcile_processos.STATUS_LOADED_LOCAL, "fixture"
        )
        return [path], urls, False, load

    def fake_ensure_datajud_parquets():
        load = reconcile_processos.SourceLoad(
            "datajud", reconcile_processos.STATUS_LOADED_LOCAL, "fixture"
        )
        return [fixture_paths["datajud_capa"]], load

    reconcile_processos.ensure_juris_parquets = fake_ensure_juris_parquets
    reconcile_processos.ensure_datajud_parquets = fake_ensure_datajud_parquets
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
