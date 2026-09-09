"""Tests for scripts/render_queries.py — RFC 0007 fail-loud data contracts."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import render_queries as rq


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_STATUS_QMD = REPO_ROOT / "web" / "src" / "queries" / "site_status.qmd"
TOTALS_QMD = REPO_ROOT / "web" / "src" / "queries" / "totals.qmd"
TRIBUNAL_COVERAGE_QMD = REPO_ROOT / "web" / "src" / "queries" / "tribunal_coverage.qmd"
COURT_RELIABILITY_QMD = REPO_ROOT / "web" / "src" / "queries" / "court_reliability.qmd"
CONSOLIDATION_STATUS_QMD = REPO_ROOT / "web" / "src" / "queries" / "consolidation_status.qmd"
STATS_COVERAGE_QMD = REPO_ROOT / "web" / "src" / "queries" / "stats_coverage.qmd"
DAILY_UPLOADS_QMD = REPO_ROOT / "web" / "src" / "queries" / "daily_uploads.qmd"


def _write_qmd(
    directory: Path,
    name: str,
    sql: str,
    *,
    output: str | None = None,
    fmt: str | None = "array",
    optional: bool | None = None,
) -> Path:
    lines = ["---"]
    if output is not None:
        lines.append(f"output: {output}")
    if fmt is not None:
        lines.append(f"format: {fmt}")
    if optional is not None:
        lines.append(f"optional: {'true' if optional else 'false'}")
    lines += ["---", "", "Prose.", "", "```{sql}", sql, "```", ""]
    path = directory / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _manifest_specs(manifest_parquet: Path) -> tuple[rq.ViewSpec, ...]:
    """A specs tuple that registers only the manifest, from a local parquet."""

    def register(con) -> bool:
        con.execute(f"CREATE VIEW manifest AS SELECT * FROM read_parquet('{manifest_parquet}')")
        return True

    return (rq.ViewSpec("manifest", register, rq.VIEW_SPECS[0].synthetic),)


@pytest.fixture
def manifest_parquet(tmp_path: Path) -> Path:
    """A local sync-manifest.parquet with the same schema as the canonical IA file."""
    import duckdb

    path = tmp_path / "sync-manifest.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-02', 'uploaded', 'available', '200', "
            "'2025-01-02T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


@pytest.fixture
def manifest_parquet_with_pending(tmp_path: Path) -> tuple[Path, datetime]:
    """A manifest with one pair DJEN confirmed available but not yet uploaded.

    Returns the parquet path and the fixed `updated_at` used for that pending
    row, so tests can assert the computed age against it.
    """
    import duckdb

    pending_updated_at = datetime.now(UTC) - timedelta(hours=48)
    path = tmp_path / "sync-manifest-pending.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-02', 'uploaded', 'available', '200', "
            "'2025-01-02T12:00:00+00:00'), "
            "('tjac', '2025-01-03', '', 'available', '200', ?)",
            [pending_updated_at],
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path, pending_updated_at


# ── parse_qmd / frontmatter ────────────────────────────────────────────────────


def test_parse_qmd_reads_optional_flag(tmp_path):
    qmd = _write_qmd(tmp_path, "q.qmd", "SELECT 1", output="/data/q.json", optional=True)
    frontmatter, sql = rq.parse_qmd(qmd)
    assert frontmatter["optional"] is True
    assert frontmatter["output"] == "/data/q.json"
    assert sql == "SELECT 1"


def test_parse_qmd_without_optional_defaults_absent(tmp_path):
    qmd = _write_qmd(tmp_path, "q.qmd", "SELECT 1", output="/data/q.json")
    frontmatter, _ = rq.parse_qmd(qmd)
    assert "optional" not in frontmatter
    assert rq.validate_frontmatter(frontmatter) == []


def test_validate_frontmatter_missing_output():
    errors = rq.validate_frontmatter({"format": "array"})
    assert any("'output'" in e for e in errors)


def test_validate_frontmatter_output_prefix():
    errors = rq.validate_frontmatter({"output": "/elsewhere/q.json", "format": "array"})
    assert any("/data/" in e for e in errors)


def test_validate_frontmatter_missing_format():
    errors = rq.validate_frontmatter({"output": "/data/q.json"})
    assert any("'format'" in e for e in errors)


def test_validate_frontmatter_bad_format():
    errors = rq.validate_frontmatter({"output": "/data/q.json", "format": "csv"})
    assert any("'format'" in e for e in errors)


def test_validate_frontmatter_non_boolean_optional():
    errors = rq.validate_frontmatter(
        {"output": "/data/q.json", "format": "array", "optional": "yes"}
    )
    assert any("'optional'" in e for e in errors)


# ── check_queries (--check) ────────────────────────────────────────────────────


def test_check_passes_valid_contract(tmp_path):
    _write_qmd(tmp_path, "ok.qmd", "SELECT COUNT(*) AS n FROM manifest", output="/data/ok.json")
    assert rq.check_queries(tmp_path) == []


def test_check_detects_unknown_column(tmp_path):
    _write_qmd(tmp_path, "bad.qmd", "SELECT no_such_column FROM manifest", output="/data/bad.json")
    failures = rq.check_queries(tmp_path)
    assert len(failures) == 1
    assert failures[0].startswith("bad.qmd:")
    assert "SQL error" in failures[0]


def test_check_detects_unknown_view(tmp_path):
    _write_qmd(tmp_path, "bad.qmd", "SELECT * FROM no_such_view", output="/data/bad.json")
    failures = rq.check_queries(tmp_path)
    assert any("no_such_view" in f for f in failures)


def test_check_detects_syntax_error(tmp_path):
    _write_qmd(tmp_path, "bad.qmd", "SELEKT 1", output="/data/bad.json")
    failures = rq.check_queries(tmp_path)
    assert any("SQL error" in f for f in failures)


def test_check_detects_frontmatter_violations(tmp_path):
    _write_qmd(tmp_path, "bad.qmd", "SELECT 1", output="/oops/bad.json", fmt="csv")
    failures = rq.check_queries(tmp_path)
    assert len(failures) == 2


def test_check_reports_missing_frontmatter(tmp_path):
    (tmp_path / "bad.qmd").write_text("no frontmatter here\n", encoding="utf-8")
    failures = rq.check_queries(tmp_path)
    assert any("frontmatter" in f for f in failures)


def test_check_empty_dir_fails(tmp_path):
    assert rq.check_queries(tmp_path) != []


def test_check_real_repo_contracts_pass():
    """The contracts shipped in web/src/queries/ must validate offline."""
    assert rq.check_queries(rq.QUERIES_DIR) == []


def test_synthetic_views_cover_all_registered_views():
    """Every render-mode view has a synthetic counterpart (single registry)."""
    import duckdb

    con = duckdb.connect()
    for spec in rq.VIEW_SPECS:
        spec.synthetic(con)
        con.execute(f"SELECT * FROM {spec.name} LIMIT 0")


# ── render_all (--strict semantics) ────────────────────────────────────────────


def test_render_writes_json_output(tmp_path, manifest_parquet):
    queries = tmp_path / "queries"
    queries.mkdir()
    public = tmp_path / "public"
    _write_qmd(
        queries,
        "totals.qmd",
        "SELECT COUNT(*) AS total FROM manifest",
        output="/data/totals.json",
        fmt="object",
    )
    count, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert count == 1
    assert failures == []
    assert (public / "data" / "totals.json").exists()


def test_render_missing_required_source_is_failure(tmp_path, manifest_parquet):
    queries = tmp_path / "queries"
    queries.mkdir()
    public = tmp_path / "public"
    _write_qmd(
        queries,
        "needs_view.qmd",
        "SELECT * FROM absent_view",
        output="/data/needs_view.json",
    )
    count, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert count == 0
    assert len(failures) == 1
    assert "needs_view.qmd" in failures[0]
    assert not (public / "data" / "needs_view.json").exists()


def test_render_missing_optional_source_warns_not_fails(tmp_path, manifest_parquet, capsys):
    queries = tmp_path / "queries"
    queries.mkdir()
    public = tmp_path / "public"
    _write_qmd(
        queries,
        "opt.qmd",
        "SELECT * FROM absent_view",
        output="/data/opt.json",
        optional=True,
    )
    count, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert count == 0
    assert failures == []
    captured = capsys.readouterr()
    assert "WARNING: optional contract skipped" in captured.err
    assert "/data/opt.json not generated" in captured.err


def test_render_invalid_frontmatter_is_failure(tmp_path, manifest_parquet):
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(queries, "nofm.qmd", "SELECT 1", output=None, fmt=None)
    _, failures = rq.render_all(queries, tmp_path / "public", _manifest_specs(manifest_parquet))
    assert any("nofm.qmd" in f for f in failures)


# ── main() exit codes ──────────────────────────────────────────────────────────


def test_main_check_exit_zero_on_valid(tmp_path, monkeypatch):
    _write_qmd(tmp_path, "ok.qmd", "SELECT 1 AS x", output="/data/ok.json")
    monkeypatch.setattr(rq, "QUERIES_DIR", tmp_path)
    assert rq.main(["--check"]) == 0


def test_main_check_exit_nonzero_on_invalid(tmp_path, monkeypatch):
    _write_qmd(tmp_path, "bad.qmd", "SELECT nope FROM manifest", output="/data/bad.json")
    monkeypatch.setattr(rq, "QUERIES_DIR", tmp_path)
    assert rq.main(["--check"]) == 1


def test_main_strict_exit_nonzero_on_required_failure(tmp_path, monkeypatch, manifest_parquet):
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(queries, "req.qmd", "SELECT * FROM absent_view", output="/data/req.json")
    monkeypatch.setattr(rq, "QUERIES_DIR", queries)
    monkeypatch.setattr(rq, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(rq, "VIEW_SPECS", _manifest_specs(manifest_parquet))
    assert rq.main(["--strict"]) == 1
    assert rq.main([]) == 0  # non-strict stays lenient


def test_main_strict_exit_zero_when_only_optional_missing(tmp_path, monkeypatch, manifest_parquet):
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(
        queries,
        "opt.qmd",
        "SELECT * FROM absent_view",
        output="/data/opt.json",
        optional=True,
    )
    _write_qmd(
        queries,
        "req.qmd",
        "SELECT COUNT(*) AS total FROM manifest",
        output="/data/req.json",
        fmt="object",
    )
    monkeypatch.setattr(rq, "QUERIES_DIR", queries)
    monkeypatch.setattr(rq, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(rq, "VIEW_SPECS", _manifest_specs(manifest_parquet))
    assert rq.main(["--strict"]) == 0


# ── _register_comunicacoes rollout fallback (RFC 0014 M2 review) ──────────────


def _copy_sql_to_parquet(path, sql):
    import duckdb

    con = duckdb.connect()
    try:
        con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def test_register_comunicacoes_falls_back_to_catalog_manifest_when_indice_missing(
    tmp_path, monkeypatch
):
    """indice_processual.parquet can 404 (deploy-web.yml can build before
    update-catalog.yml ever publishes it — see the module-level comment on
    _IA_CATALOG_MANIFEST_URL). Without a fallback, processos_multi_fonte.qmd
    would regress from real DJEN data to empty for however long that takes.
    """
    import duckdb

    comunicacoes = _copy_sql_to_parquet(
        tmp_path / "comunicacoes.parquet",
        """
        SELECT * FROM (VALUES
            ('00000010220248220001', DATE '2024-03-01', 'TJRO')
        ) AS t(numero_processo, data_disponibilizacao, tribunal)
        """,
    )
    catalog = _copy_sql_to_parquet(
        tmp_path / "catalog.parquet",
        f"SELECT '{comunicacoes}' AS ia_url, 'comunicacoes' AS table_name",
    )
    monkeypatch.setattr(rq, "_IA_CATALOG_MANIFEST_URL", str(catalog))
    # Index unreachable: dest doesn't exist locally, and the "IA" URL refuses
    # the connection immediately (no real network involved).
    monkeypatch.setattr(rq, "_INDICE_PROCESSUAL_PARQUET", tmp_path / "indice_processual.parquet")
    monkeypatch.setattr(rq, "_INDICE_PROCESSUAL_IA_URL", "http://127.0.0.1:1/unreachable")

    con = duckdb.connect()
    try:
        registered = rq._register_comunicacoes(con)
        assert registered is True
        rows = con.execute("SELECT numero_processo FROM comunicacoes").fetchall()
    finally:
        con.close()
    assert rows == [("00000010220248220001",)]


def test_register_comunicacoes_prefers_indice_when_available(tmp_path, monkeypatch):
    import duckdb

    comunicacoes = _copy_sql_to_parquet(
        tmp_path / "comunicacoes.parquet",
        """
        SELECT * FROM (VALUES
            ('00000010220248220001', DATE '2024-03-01', 'TJRO')
        ) AS t(numero_processo, data_disponibilizacao, tribunal)
        """,
    )
    indice = _copy_sql_to_parquet(
        tmp_path / "indice_processual.parquet",
        f"""
        SELECT '00000010220248220001' AS numero_processo, 'djen' AS fonte,
            'c1' AS registro_id, 'TJRO' AS tribunal, DATE '2024-03-01' AS data,
            '{comunicacoes}' AS arquivo_ia_url
        """,
    )
    monkeypatch.setattr(rq, "_INDICE_PROCESSUAL_PARQUET", indice)
    # A wrong/unreachable catalog URL proves the fallback was never touched —
    # if it had been used, this would raise instead of quietly succeeding.
    monkeypatch.setattr(rq, "_IA_CATALOG_MANIFEST_URL", "http://127.0.0.1:1/unreachable")

    con = duckdb.connect()
    try:
        registered = rq._register_comunicacoes(con)
        assert registered is True
        rows = con.execute("SELECT numero_processo FROM comunicacoes").fetchall()
    finally:
        con.close()
    assert rows == [("00000010220248220001",)]


# ── _register_tjro_juris / _register_datajud_capa IA fallback ─────────────────
# deploy-web.yml's fresh checkout never runs reconcile_processos.py, and even
# update-catalog.yml's own job caches its IA-fallback downloads under
# data/reconcile-cache/ rather than the directories these two functions used
# to glob — so, before this fix, they returned False (and the corresponding
# .qmd contracts silently skipped) in every real CI environment whenever the
# source wasn't a pre-existing local file. Delegating to
# reconcile_processos.ensure_juris_parquets()/ensure_datajud_parquets() (the
# same local-then-IA logic the reconciler itself already relies on and tests)
# fixes this without duplicating the IA item discovery.


def test_register_datajud_capa_falls_back_to_ia_when_local_absent(tmp_path, monkeypatch):
    from scripts import reconcile_processos as rp

    datajud_parquet = _copy_sql_to_parquet(
        tmp_path / "datajud-capa-tjro.parquet",
        """
        SELECT '00000010220248220001' AS numero_processo, 'TJRO' AS tribunal,
            'Execução Fiscal' AS classe_nome
        """,
    )

    def fake_ensure_datajud_parquets():
        load = rp.SourceLoad("datajud", rp.STATUS_LOADED_REMOTE, "IA item(s) datajud-tjro")
        return [datajud_parquet], load

    # No local files exist under tmp_path's isolated cwd, so the pre-fix glob
    # would find nothing — only the IA-fallback path below can succeed.
    monkeypatch.setattr(rp, "ensure_datajud_parquets", fake_ensure_datajud_parquets)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_datajud_capa(con)
        assert registered is True
        rows = con.execute("SELECT numero_processo FROM datajud_capa").fetchall()
    finally:
        con.close()
    assert rows == [("00000010220248220001",)]


def test_register_tjro_juris_falls_back_to_ia_when_local_absent(tmp_path, monkeypatch):
    from scripts import reconcile_processos as rp

    juris_parquet = _copy_sql_to_parquet(
        tmp_path / "tjro-juris-2024.parquet",
        """
        SELECT 'd1' AS id_documento, 'ACÓRDÃO' AS tipo,
            DATE '2024-05-01' AS data_julgamento,
            TIMESTAMP '2024-05-02 00:00:00' AS extraido_em
        """,
    )

    def fake_ensure_juris_parquets():
        load = rp.SourceLoad("juris", rp.STATUS_LOADED_REMOTE, "IA item(s) tjro-juris-2024")
        return [juris_parquet], {}, False, load

    monkeypatch.setattr(rp, "ensure_juris_parquets", fake_ensure_juris_parquets)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_tjro_juris(con)
        assert registered is True
        rows = con.execute("SELECT id_documento FROM tjro_juris").fetchall()
    finally:
        con.close()
    assert rows == [("d1",)]


def test_register_tjro_juris_dedups_overlapping_ia_shards(tmp_path, monkeypatch):
    """needs_dedup=True (overlapping monthly IA shards) must not double-count.

    Mirrors reconcile_processos.py's own _register_juris dedup: same
    id_documento keeps only the row with the most recent extraido_em.
    """
    from scripts import reconcile_processos as rp

    shard_a = _copy_sql_to_parquet(
        tmp_path / "2024-05-ACORDAO.parquet",
        """
        SELECT 'd1' AS id_documento, 'ACÓRDÃO' AS tipo,
            DATE '2024-05-01' AS data_julgamento,
            TIMESTAMP '2024-05-02 00:00:00' AS extraido_em
        """,
    )
    shard_b = _copy_sql_to_parquet(
        tmp_path / "2024-06-ACORDAO.parquet",
        """
        SELECT 'd1' AS id_documento, 'ACÓRDÃO' AS tipo,
            DATE '2024-05-01' AS data_julgamento,
            TIMESTAMP '2024-06-01 00:00:00' AS extraido_em
        """,
    )

    def fake_ensure_juris_parquets():
        load = rp.SourceLoad("juris", rp.STATUS_LOADED_REMOTE, "IA item(s) tjro-juris-2024")
        return [shard_a, shard_b], {}, True, load

    monkeypatch.setattr(rp, "ensure_juris_parquets", fake_ensure_juris_parquets)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_tjro_juris(con)
        assert registered is True
        rows = con.execute("SELECT id_documento, extraido_em FROM tjro_juris").fetchall()
    finally:
        con.close()
    assert len(rows) == 1
    assert rows[0][0] == "d1"


# ── _register_lawyer_ratings / _register_ratings_history IA fallback ──────────
# deploy-web.yml's fresh checkout never populates data/parquets/, and neither
# does test.yml's --check mode -- so, before this fix, these two functions
# returned False (and lawyer_leaderboard.qmd, being optional, silently
# skipped) in every real CI environment. scripts/pipeline/export_ratings.py
# (run by consolidate-parquet.yml) uploads lawyer_ratings.parquet and
# ratings_history.parquet to the causaganha-catalog IA item -- the same
# fallback pattern _register_acordaos already uses for the STJ parquet.


def test_register_lawyer_ratings_falls_back_to_ia_when_local_absent(tmp_path, monkeypatch):
    ia_parquet = _copy_sql_to_parquet(
        tmp_path / "ia-lawyer_ratings.parquet",
        """
        SELECT 'Fulano de Tal' AS lawyer_name, '12345' AS oab_number,
            'RO' AS oab_state, 30.0 AS rating
        """,
    )
    monkeypatch.setattr(rq, "DEV_RATINGS_DIR", tmp_path / "no-such-dir")

    def fake_try_download_parquet(url, dest, label):
        assert url == rq._LAWYER_RATINGS_IA_URL
        return ia_parquet

    monkeypatch.setattr(rq, "_try_download_parquet", fake_try_download_parquet)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_lawyer_ratings(con)
        assert registered is True
        rows = con.execute("SELECT lawyer_name FROM lawyer_ratings").fetchall()
    finally:
        con.close()
    assert rows == [("Fulano de Tal",)]


def test_register_ratings_history_falls_back_to_ia_when_local_absent(tmp_path, monkeypatch):
    ia_parquet = _copy_sql_to_parquet(
        tmp_path / "ia-ratings_history.parquet",
        """
        SELECT 'Fulano de Tal' AS lawyer_name, DATE '2024-01-01' AS data, 25.0 AS rating
        """,
    )
    monkeypatch.setattr(rq, "DEV_RATINGS_DIR", tmp_path / "no-such-dir")

    def fake_try_download_parquet(url, dest, label):
        assert url == rq._RATINGS_HISTORY_IA_URL
        return ia_parquet

    monkeypatch.setattr(rq, "_try_download_parquet", fake_try_download_parquet)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_ratings_history(con)
        assert registered is True
        rows = con.execute("SELECT lawyer_name FROM ratings_history").fetchall()
    finally:
        con.close()
    assert rows == [("Fulano de Tal",)]


def test_register_lawyer_ratings_prefers_local_over_ia(tmp_path, monkeypatch):
    """A pre-existing local file (dev workflow) must not trigger a network call."""
    dev_dir = tmp_path / "parquets"
    dev_dir.mkdir()
    local_parquet = _copy_sql_to_parquet(
        dev_dir / "lawyer_ratings.parquet",
        "SELECT 'Local Lawyer' AS lawyer_name",
    )
    monkeypatch.setattr(rq, "DEV_RATINGS_DIR", dev_dir)

    def fail_if_called(url, dest, label):
        pytest.fail("must not attempt IA download when local file exists")

    monkeypatch.setattr(rq, "_try_download_parquet", fail_if_called)

    con = __import__("duckdb").connect()
    try:
        registered = rq._register_lawyer_ratings(con)
        assert registered is True
        rows = con.execute("SELECT lawyer_name FROM lawyer_ratings").fetchall()
    finally:
        con.close()
    assert rows == [("Local Lawyer",)]
    assert local_parquet.exists()


# ── site_status.qmd — pending_real_max_age_hours (#924 §3.4) ──────────────────


def test_site_status_reports_pending_real_max_age_hours(tmp_path, manifest_parquet_with_pending):
    """The literal publication→archive SLO age, not just a pending count.

    docs/SERVICE_OBJECTIVES.md documents `pending_real` (a count) as a coarse
    proxy for the declared 24h SLO. `pending_real_max_age_hours` closes that
    gap: the age, in hours, of the oldest pair DJEN confirmed available
    (djen_raw='200') but still missing from IA (ia_status != 'uploaded').
    """
    manifest_parquet, pending_updated_at = manifest_parquet_with_pending
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "site_status.qmd").write_text(SITE_STATUS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    count, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert failures == []
    assert count == 1

    payload = json.loads((public / "data" / "site-status.json").read_text())
    djen = payload["sources"]["djen"]
    assert djen["pending_real"] == 1

    expected_age_hours = (datetime.now(UTC) - pending_updated_at).total_seconds() / 3600
    assert djen["pending_real_max_age_hours"] == pytest.approx(expected_age_hours, abs=0.05)


def test_site_status_pending_real_max_age_hours_is_null_when_nothing_pending(
    tmp_path, manifest_parquet
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "site_status.qmd").write_text(SITE_STATUS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert failures == []

    payload = json.loads((public / "data" / "site-status.json").read_text())
    djen = payload["sources"]["djen"]
    assert djen["pending_real"] == 0
    assert djen["pending_real_max_age_hours"] is None


# ── tribunal_calendar partitioning (#1191) ──────────────────────────────────────
#
# /stats' drill-down island only ever needs one tribunal's rows at a time, but
# used to receive the whole tribunal_calendar contract (every tribunal x date
# in the archive) as a client:only prop, which serializes it whole into the
# page for hydration. render_all() now also splits the rendered
# tribunal_calendar.json into one small file per tribunal — same canonical
# contract, no second source of truth — so the frontend can fetch only the
# tribunal it needs.

_TRIBUNAL_CALENDAR_SQL = """
SELECT
  tribunal,
  date,
  CASE
    WHEN ia_status = 'uploaded' THEN 'uploaded'
    WHEN djen_status = 'absent' THEN 'absent'
  END AS status
FROM manifest
WHERE ia_status = 'uploaded' OR djen_status = 'absent'
ORDER BY tribunal, date
"""


@pytest.fixture
def manifest_parquet_multi_tribunal(tmp_path: Path) -> Path:
    """A manifest spanning two tribunals, for partition-by-tribunal tests."""
    import duckdb

    path = tmp_path / "sync-manifest-multi.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-01', 'uploaded', 'available', '200', "
            "'2025-01-01T12:00:00+00:00'), "
            "('tjro', '2025-01-02', '', 'absent', '404', "
            "'2025-01-02T12:00:00+00:00'), "
            "('tjsp', '2025-06-01', '', 'absent', '400', "
            "'2025-06-01T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def test_render_partitions_tribunal_calendar_by_tribunal(tmp_path, manifest_parquet_multi_tribunal):
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(
        queries,
        "tribunal_calendar.qmd",
        _TRIBUNAL_CALENDAR_SQL,
        output="/data/tribunal_calendar.json",
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet_multi_tribunal))
    assert failures == []

    tjro = json.loads((public / "data" / "tribunal_calendar_by_tribunal" / "tjro.json").read_text())
    assert tjro == [
        {"tribunal": "tjro", "date": "2025-01-01", "status": "uploaded"},
        {"tribunal": "tjro", "date": "2025-01-02", "status": "absent"},
    ]

    tjsp = json.loads((public / "data" / "tribunal_calendar_by_tribunal" / "tjsp.json").read_text())
    assert tjsp == [{"tribunal": "tjsp", "date": "2025-06-01", "status": "absent"}]


def test_tribunal_calendar_partitions_have_parity_with_the_canonical_contract(
    tmp_path, manifest_parquet_multi_tribunal
):
    """Every row in the canonical contract appears in exactly one partition."""
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(
        queries,
        "tribunal_calendar.qmd",
        _TRIBUNAL_CALENDAR_SQL,
        output="/data/tribunal_calendar.json",
    )
    public = tmp_path / "public"

    rq.render_all(queries, public, _manifest_specs(manifest_parquet_multi_tribunal))

    canonical = json.loads((public / "data" / "tribunal_calendar.json").read_text())
    partitioned: list[dict] = []
    for partition_file in sorted(
        (public / "data" / "tribunal_calendar_by_tribunal").glob("*.json")
    ):
        partitioned.extend(json.loads(partition_file.read_text()))

    key = lambda row: (row["tribunal"], row["date"])  # noqa: E731
    assert sorted(partitioned, key=key) == sorted(canonical, key=key)


def test_render_without_tribunal_calendar_contract_writes_no_partitions(tmp_path, manifest_parquet):
    """No tribunal_calendar.qmd in this build (or contract absent) → no partition dir."""
    queries = tmp_path / "queries"
    queries.mkdir()
    _write_qmd(
        queries,
        "totals.qmd",
        "SELECT COUNT(*) AS total FROM manifest",
        output="/data/totals.json",
        fmt="object",
    )
    public = tmp_path / "public"

    rq.render_all(queries, public, _manifest_specs(manifest_parquet))

    assert not (public / "data" / "tribunal_calendar_by_tribunal").exists()


# ── absent must not double-count an already-uploaded row (#continuity) ──────
#
# SyncManifest.mark_ia_uploaded() (manifest.py) flips ia_status to 'uploaded'
# for any date IA reports as archived, without ever clearing a stale
# djen_status='absent' left over from an earlier check -- so a manifest row
# with BOTH ia_status='uploaded' and djen_status='absent' is a reachable live
# state, not a theoretical one. Every other place that resolves this same
# ambiguity already treats 'uploaded' as authoritative over a stale 'absent'
# (SyncManifest._categorize(), render_manifest_parquet.py's _apply_deltas,
# and this same test file's own _TRIBUNAL_CALENDAR_SQL above). These three
# reporting queries' own 'pending'/'unknown' filters already guard with
# 'AND ia_status != uploaded' -- their 'absent' filter must too.


@pytest.fixture
def manifest_parquet_uploaded_and_stale_absent(tmp_path: Path) -> Path:
    """One row that is both ia_status='uploaded' and a stale djen_status='absent'."""
    import duckdb

    path = tmp_path / "sync-manifest-uploaded-absent.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-02', 'uploaded', 'absent', '404', "
            "'2025-01-02T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


@pytest.fixture
def manifest_parquet_null_djen_status(tmp_path: Path) -> Path:
    """A row downgraded to unknown the way render_manifest_parquet.py's
    _normalize_manifest actually does it in production: SQL NULL, not ''.
    """
    import duckdb

    path = tmp_path / "sync-manifest-null-djen-status.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-02', '', NULL, NULL, '2025-01-02T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


@pytest.fixture
def manifest_parquet_confirmed_pending(tmp_path: Path) -> Path:
    """One row probe-confirmed available but not yet uploaded, as written by

    src/djen_backup/probe.py's mark_confirmed() -> segments.py, merged as-is
    into the canonical parquet by render_manifest_parquet.py's _apply_deltas
    (djen_status='confirmed' is never rewritten to 'available' there --
    only write_back_csv's legacy CSV export folds it, per that function's
    own docstring).
    """
    import duckdb

    path = tmp_path / "sync-manifest-confirmed.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-02', '', 'confirmed', '200', "
            "'2025-01-02T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def test_totals_counts_confirmed_row_as_pending(tmp_path, manifest_parquet_confirmed_pending):
    """djen_status='confirmed' is a real parquet/drain-only refinement of

    'available' (probe.py's mark_confirmed, prioritised by drain.py and
    already folded into 'pending' by render_manifest_parquet.py's own
    _print_merge_stats) -- it must not vanish from every displayed bucket.
    """
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "totals.qmd").write_text(TOTALS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_confirmed_pending)
    )
    assert failures == []

    payload = json.loads((public / "data" / "totals.json").read_text())
    assert payload["pending"] == 1
    assert (
        payload["uploaded"] + payload["pending"] + payload["absent"] + payload["unknown"]
        == payload["total"]
    )


def test_tribunal_coverage_counts_confirmed_row_as_pending(
    tmp_path, manifest_parquet_confirmed_pending
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "tribunal_coverage.qmd").write_text(
        TRIBUNAL_COVERAGE_QMD.read_text(encoding="utf-8")
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_confirmed_pending)
    )
    assert failures == []

    rows = json.loads((public / "data" / "tribunal_coverage.json").read_text())
    assert len(rows) == 1
    row = rows[0]
    assert row["pending"] == 1
    assert row["uploaded"] + row["pending"] + row["absent"] + row["unknown"] == row["total"]


def test_totals_counts_null_djen_status_row_as_unknown(tmp_path, manifest_parquet_null_djen_status):
    """A row whose djen_status is SQL NULL (as _normalize_manifest's downgrade

    actually writes it) must still land in one of the displayed buckets --
    otherwise it counts toward `total` while vanishing from
    uploaded+pending+absent+unknown, since `djen_status = ''` is NULL (not
    true) when djen_status IS NULL.
    """
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "totals.qmd").write_text(TOTALS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet_null_djen_status))
    assert failures == []

    payload = json.loads((public / "data" / "totals.json").read_text())
    assert payload["total"] == 1
    assert payload["unknown"] == 1
    assert (
        payload["uploaded"] + payload["pending"] + payload["absent"] + payload["unknown"]
        == payload["total"]
    )


def test_tribunal_coverage_counts_null_djen_status_row_as_unknown(
    tmp_path, manifest_parquet_null_djen_status
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "tribunal_coverage.qmd").write_text(
        TRIBUNAL_COVERAGE_QMD.read_text(encoding="utf-8")
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet_null_djen_status))
    assert failures == []

    rows = json.loads((public / "data" / "tribunal_coverage.json").read_text())
    assert len(rows) == 1
    row = rows[0]
    assert row["unknown"] == 1
    assert row["uploaded"] + row["pending"] + row["absent"] + row["unknown"] == row["total"]


def test_totals_does_not_double_count_uploaded_row_as_absent(
    tmp_path, manifest_parquet_uploaded_and_stale_absent
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "totals.qmd").write_text(TOTALS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_uploaded_and_stale_absent)
    )
    assert failures == []

    payload = json.loads((public / "data" / "totals.json").read_text())
    assert payload["uploaded"] == 1
    assert payload["absent"] == 0
    assert (
        payload["uploaded"] + payload["pending"] + payload["absent"] + payload["unknown"]
        == payload["total"]
    )


def test_tribunal_coverage_does_not_double_count_uploaded_row_as_absent(
    tmp_path, manifest_parquet_uploaded_and_stale_absent
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "tribunal_coverage.qmd").write_text(
        TRIBUNAL_COVERAGE_QMD.read_text(encoding="utf-8")
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_uploaded_and_stale_absent)
    )
    assert failures == []

    rows = json.loads((public / "data" / "tribunal_coverage.json").read_text())
    assert len(rows) == 1
    row = rows[0]
    assert row["uploaded"] == 1
    assert row["absent"] == 0
    assert row["uploaded"] + row["pending"] + row["absent"] + row["unknown"] == row["total"]


def test_court_reliability_does_not_double_count_uploaded_row_as_absent(
    tmp_path, manifest_parquet_uploaded_and_stale_absent
):
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "court_reliability.qmd").write_text(
        COURT_RELIABILITY_QMD.read_text(encoding="utf-8")
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_uploaded_and_stale_absent)
    )
    assert failures == []

    rows = json.loads((public / "data" / "court_reliability.json").read_text())
    assert len(rows) == 1
    row = rows[0]
    assert row["collected"] == 1
    assert row["absent"] == 0
    assert row["total"] == 1
    assert row["rate"] == 1.0


# ── consolidation_status must not hardcode the tribunal roster size ─────────
#
# consolidation_status.qmd classified a date as "fully uploaded" via
# `tribunals_uploaded >= 90`, a literal that happened to match
# src/causaganha/config.py's TRIBUNAIS count (96) loosely at the time it was
# written but is never actually derived from it. Any manifest that doesn't
# happen to track >=90 tribunals -- a smaller test fixture, an early period
# of the roster's history, or a future roster change -- can never produce a
# single "fully uploaded" date, no matter how complete daily coverage
# actually is for the tribunals the manifest does track.


@pytest.fixture
def manifest_parquet_small_tribunal_universe(tmp_path: Path) -> Path:
    """A manifest tracking only 3 tribunals: one date fully covered by all
    three, one date covered by only two of the three (a straggler).
    """
    import duckdb

    path = tmp_path / "sync-manifest-small-universe.parquet"
    con = duckdb.connect()
    try:
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            "('tjro', '2025-01-01', 'uploaded', 'available', '200', "
            "'2025-01-01T12:00:00+00:00'), "
            "('tjac', '2025-01-01', 'uploaded', 'available', '200', "
            "'2025-01-01T12:00:00+00:00'), "
            "('tjsp', '2025-01-01', 'uploaded', 'available', '200', "
            "'2025-01-01T12:00:00+00:00'), "
            "('tjro', '2025-01-02', 'uploaded', 'available', '200', "
            "'2025-01-02T12:00:00+00:00'), "
            "('tjac', '2025-01-02', 'uploaded', 'available', '200', "
            "'2025-01-02T12:00:00+00:00'), "
            "('tjsp', '2025-01-02', '', 'available', '200', "
            "'2025-01-02T12:00:00+00:00')"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def test_consolidation_status_counts_a_date_with_every_tracked_tribunal_as_fully_uploaded(
    tmp_path, manifest_parquet_small_tribunal_universe
):
    """2025-01-01 has all 3 of the manifest's 3 tracked tribunals uploaded --

    it must count as a fully uploaded date. A hardcoded ">=90" threshold can
    never be satisfied by a 3-tribunal manifest, so this fails against the
    unfixed query (dates_fully_uploaded == 0) and passes once the threshold
    is derived from the manifest's own distinct tribunal count.
    """
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "consolidation_status.qmd").write_text(
        CONSOLIDATION_STATUS_QMD.read_text(encoding="utf-8")
    )
    public = tmp_path / "public"

    _, failures = rq.render_all(
        queries, public, _manifest_specs(manifest_parquet_small_tribunal_universe)
    )
    assert failures == []

    payload = json.loads((public / "data" / "consolidation_status.json").read_text())
    assert payload["total_dates_with_uploads"] == 2
    assert payload["dates_fully_uploaded"] == 1
    assert payload["dates_partially_uploaded"] == 1


# ── "last N days" window boundaries (stats_coverage / daily_uploads) ───────────


@pytest.fixture
def manifest_parquet_30_day_window(tmp_path: Path) -> tuple[Path, str]:
    """31 dates spanning stats_coverage's 'last 30 days' window.

    The boundary date (exactly 30 days before CURRENT_DATE) has 3 distinct
    tribunals uploaded; every one of the 30 days after it (today-29..today)
    has exactly 1. A query that correctly counts only 30 days never sees the
    boundary's outlier count of 3. Returns (parquet_path, boundary_date_iso).
    """
    import duckdb

    path = tmp_path / "sync-manifest-30-day-window.parquet"
    con = duckdb.connect()
    try:
        today = con.execute("SELECT CURRENT_DATE").fetchone()[0]
        boundary = today - timedelta(days=30)
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            f"('tjro', '{boundary.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjac', '{boundary.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjba', '{boundary.isoformat()}', 'uploaded', 'available', '200', now())"
        )
        for offset in range(29, -1, -1):
            day = (today - timedelta(days=offset)).isoformat()
            con.execute(
                "INSERT INTO manifest VALUES "
                f"('tjro', '{day}', 'uploaded', 'available', '200', now())"
            )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path, boundary.isoformat()


def test_stats_coverage_last_30_days_excludes_the_31st_boundary_day(
    tmp_path, manifest_parquet_30_day_window
):
    """web/src/pages/stats.astro labels this card 'Últimos 30 dias' -- the

    query must reflect exactly 30 distinct dates, not 31. The boundary date
    (today-30) is rigged with an outlier collected-count of 3 (every other
    date has 1); if the window wrongly includes it, avg_coverage/best_count
    pick it up.
    """
    manifest_parquet, boundary_iso = manifest_parquet_30_day_window
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "stats_coverage.qmd").write_text(STATS_COVERAGE_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert failures == []

    payload = json.loads((public / "data" / "stats_coverage.json").read_text())
    assert payload["best_count"] == 1
    assert payload["worst_count"] == 1
    assert payload["avg_coverage"] == 1.0
    assert payload["best_day"] != boundary_iso
    assert payload["worst_day"] != boundary_iso


@pytest.fixture
def manifest_parquet_stats_coverage_with_in_flight_day(tmp_path: Path) -> tuple[Path, str, str]:
    """Three recent days, only one of them genuinely the worst.

    - 5 days ago: all 3 tribunals uploaded (collected=3) -- settled, best day.
    - 2 days ago: 2 uploaded + 1 djen-confirmed absent (404, settled) --
      collected=2, the true worst *settled* day.
    - today: 1 uploaded + 2 still `pending_real` (djen_raw='200', not yet
      uploaded -- DJEN confirmed the caderno exists but the archival hasn't
      caught up, same 'pending_real' CLAUDE.md/site_status.qmd concept, well
      within the 24h SLO) -- collected=1, lower than the settled worst day,
      but not a genuine coverage failure: it just hasn't finished yet.

    Returns (parquet_path, best_day_iso, worst_settled_day_iso).
    """
    import duckdb

    path = tmp_path / "sync-manifest-stats-coverage-in-flight.parquet"
    con = duckdb.connect()
    try:
        today = con.execute("SELECT CURRENT_DATE").fetchone()[0]
        best_day = today - timedelta(days=5)
        worst_settled_day = today - timedelta(days=2)
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            f"('tjro', '{best_day.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjac', '{best_day.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjba', '{best_day.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjro', '{worst_settled_day.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjac', '{worst_settled_day.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjba', '{worst_settled_day.isoformat()}', '', 'absent', '404', now()), "
            f"('tjro', '{today.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjac', '{today.isoformat()}', '', 'available', '200', now()), "
            f"('tjba', '{today.isoformat()}', '', 'available', '200', now())"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path, best_day.isoformat(), worst_settled_day.isoformat()


def test_stats_coverage_worst_day_excludes_still_in_flight_day(
    tmp_path, manifest_parquet_stats_coverage_with_in_flight_day
):
    """'Pior dia' (web/src/pages/stats.astro) must name a real coverage

    failure, not today's still-converging numbers. collect-zips.yml itself
    never checks 'today' (src/djen_backup/__main__.py's default end_date is
    yesterday) precisely because a partial day looks artificially bad --
    stats_coverage.qmd must apply the same 'not settled yet' exclusion
    site_status.qmd already uses for its own pending_real/absent_confirmed
    split, not just a same-day exclusion.
    """
    manifest_parquet, best_day_iso, worst_settled_day_iso = (
        manifest_parquet_stats_coverage_with_in_flight_day
    )
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "stats_coverage.qmd").write_text(STATS_COVERAGE_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert failures == []

    payload = json.loads((public / "data" / "stats_coverage.json").read_text())
    assert payload["worst_day"] == worst_settled_day_iso
    assert payload["worst_count"] == 2
    assert payload["best_day"] == best_day_iso
    assert payload["best_count"] == 3


@pytest.fixture
def manifest_parquet_120_day_window(tmp_path: Path) -> tuple[Path, str]:
    """Two dates only, straddling daily_uploads's 'last 120 days' boundary:

    exactly 120 days before CURRENT_DATE (must be excluded) and 119 days
    before (must be included). Returns (parquet_path, boundary_date_iso).
    """
    import duckdb

    path = tmp_path / "sync-manifest-120-day-window.parquet"
    con = duckdb.connect()
    try:
        today = con.execute("SELECT CURRENT_DATE").fetchone()[0]
        boundary = today - timedelta(days=120)
        inside = today - timedelta(days=119)
        con.execute(
            """
            CREATE TABLE manifest (
                tribunal VARCHAR, date DATE, ia_status VARCHAR,
                djen_status VARCHAR, djen_raw VARCHAR, updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT INTO manifest VALUES "
            f"('tjro', '{boundary.isoformat()}', 'uploaded', 'available', '200', now()), "
            f"('tjro', '{inside.isoformat()}', 'uploaded', 'available', '200', now())"
        )
        con.execute(f"COPY manifest TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path, boundary.isoformat()


def test_daily_uploads_last_120_days_excludes_the_121st_boundary_day(
    tmp_path, manifest_parquet_120_day_window
):
    """daily_uploads.qmd's own description promises 'last 120 days' -- the

    boundary date (today-120) must not appear in the rendered rows.
    """
    manifest_parquet, boundary_iso = manifest_parquet_120_day_window
    queries = tmp_path / "queries"
    queries.mkdir()
    (queries / "daily_uploads.qmd").write_text(DAILY_UPLOADS_QMD.read_text(encoding="utf-8"))
    public = tmp_path / "public"

    _, failures = rq.render_all(queries, public, _manifest_specs(manifest_parquet))
    assert failures == []

    rows = json.loads((public / "data" / "daily_uploads.json").read_text())
    dates = [row["date"] for row in rows]
    assert boundary_iso not in dates
    assert len(rows) == 1
