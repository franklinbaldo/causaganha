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
