"""Tests for scripts/reconcile_processos.py — IA fallback + source coverage.

The full-reconcile tests run with NO local source parquets: JURIS and DataJud
are served exclusively through the Internet Archive fallback (respx-mocked
httpx), the DJEN catalog manifest is a local parquet whose ia_url entries
point at local fixture parquets, and STJ is fetched via its (mocked) IA URL.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import duckdb
import pytest
import respx

from datajud.archive import write_capa_parquet
from scripts import reconcile_processos as rp


if TYPE_CHECKING:
    from pathlib import Path

# Two valid 20-digit CNJs. CNJ_ALL appears in every source; CNJ_DJEN_DJ only
# in DJEN + DataJud.
CNJ_ALL = "00000010220248220001"
CNJ_DJEN_DJ = "00000020320248220002"


def _copy_sql_to_parquet(path: Path, sql: str) -> Path:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def _comunicacoes_parquet(path: Path) -> Path:
    return _copy_sql_to_parquet(
        path,
        f"""
        SELECT * FROM (VALUES
            ('0000001-02.2024.8.22.0001', DATE '2024-03-01', 'TJRO'),
            ('{CNJ_ALL}',                 DATE '2024-03-05', 'TJRO'),
            ('{CNJ_DJEN_DJ}',             DATE '2024-04-01', 'TJRO')
        ) AS t(numero_processo, data_disponibilizacao, tribunal)
        """,
    )


def _catalog_parquet(path: Path, comunicacoes_paths: list[Path]) -> Path:
    """A causaganha-catalog manifest whose ia_url entries are local paths."""
    if comunicacoes_paths:
        values = ", ".join(f"('{p}', 'comunicacoes')" for p in comunicacoes_paths)
    else:
        values = "('unused', 'other_table')"
    return _copy_sql_to_parquet(path, f"SELECT * FROM (VALUES {values}) AS t(ia_url, table_name)")


def _juris_parquet(path: Path, rows: str) -> Path:
    return _copy_sql_to_parquet(
        path,
        f"""
        SELECT * FROM (VALUES {rows})
        AS t(id_documento, nr_processo, tipo, classe_judicial, orgao, relator,
             sistema_origem, data_julgamento, texto_limpo, url_portal, extraido_em)
        """,
    )


def _stj_parquet(path: Path, numero_processo: str = CNJ_ALL) -> Path:
    return _copy_sql_to_parquet(
        path,
        f"""
        SELECT * FROM (VALUES
            ('stj-1', '{numero_processo}', 'REsp', 'MIN X', 'tema', 'tese', 'ementa',
             DATE '2024-05-01', DATE '2024-05-10')
        ) AS t(id, "numeroProcesso", "siglaClasse", "ministroRelator", tema,
               "teseJuridica", ementa, "dataDecisao", "dataPublicacao")
        """,
    )


def _datajud_capa_bytes(path: Path) -> bytes:
    rows = [
        {
            "numero_processo": CNJ_ALL,
            "tribunal": "tjro",
            "grau": "G2",
            "orgao_julgador": "2a Camara",
            "classe_nome": "Apelacao Civel",
            "assuntos": "Contratos",
            "data_ajuizamento": "2024-01-10T00:00:00",
            "ultima_atualizacao": "2024-06-01T00:00:00",
        },
        {
            "numero_processo": CNJ_DJEN_DJ,
            "tribunal": "tjro",
            "grau": "G1",
            "orgao_julgador": "1a Vara",
            "classe_nome": "Procedimento Comum",
            "assuntos": "Consumidor",
            "data_ajuizamento": "2024-02-20T00:00:00",
            "ultima_atualizacao": "2024-06-02T00:00:00",
        },
    ]
    write_capa_parquet(rows, path)
    return path.read_bytes()


@pytest.fixture
def isolated_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every module-level path at tmp_path so no repo data leaks in."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(rp, "ROOT", tmp_path)  # JURIS local globs find nothing
    monkeypatch.setattr(rp, "DATA_DIR", data_dir)
    monkeypatch.setattr(rp, "_PARQUET_UNIFICADOS", data_dir / "processos_unificados.parquet")
    monkeypatch.setattr(rp, "_PARQUET_DOCUMENTOS", data_dir / "processo_documentos.parquet")
    monkeypatch.setattr(rp, "_STJ_PARQUET", data_dir / "stj" / "stj-acordaos.parquet")
    monkeypatch.setattr(rp, "_DATAJUD_DIR", data_dir / "datajud")
    monkeypatch.setenv("RECONCILE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("RECONCILE_EXPECTED_SOURCES", raising=False)
    monkeypatch.delenv("RECONCILE_STRICT", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    return tmp_path


def _mock_juris_remote(router: respx.MockRouter, fixtures: Path) -> None:
    """Serve two overlapping monthly JURIS shards from a fake tjro-juris-2024 item."""
    # id_documento 1 appears in BOTH shards (recrawl overlap) — the loader
    # must dedup it; id 2 is unique to the second shard.
    juris1 = _juris_parquet(
        fixtures / "2024-01-ACORDAO.parquet",
        f"(1, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A', 'PJE',"
        " '2024-01-15', 'texto um', 'https://juris/1', '2024-01-31T00:00:00')",
    )
    juris2 = _juris_parquet(
        fixtures / "2024-02-SENTENCA.parquet",
        f"(1, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A', 'PJE',"
        " '2024-01-15', 'texto um', 'https://juris/1', '2024-02-28T00:00:00'),"
        f"(2, '{CNJ_ALL}', 'SENTENÇA', 'Apelação', '1a Vara', 'Juiz B', 'PJE',"
        " '2024-02-10', 'texto dois', 'https://juris/2', '2024-02-28T00:00:00')",
    )
    router.get(host="archive.org", path="/advancedsearch.php").respond(
        200, json={"response": {"docs": [{"identifier": "tjro-juris-2024"}]}}
    )
    router.get(host="archive.org", path="/metadata/tjro-juris-2024").respond(
        200,
        json={
            "files": [
                {"name": "2024-01-ACORDAO.parquet"},
                {"name": "2024-02-SENTENCA.parquet"},
                {"name": "tjro-juris-2024_meta.xml"},
            ]
        },
    )
    router.get(
        host="archive.org", path="/download/tjro-juris-2024/2024-01-ACORDAO.parquet"
    ).respond(200, content=juris1.read_bytes())
    router.get(
        host="archive.org", path="/download/tjro-juris-2024/2024-02-SENTENCA.parquet"
    ).respond(200, content=juris2.read_bytes())


def _mock_datajud_remote(router: respx.MockRouter, fixtures: Path) -> None:
    capa_bytes = _datajud_capa_bytes(fixtures / "datajud-capa-tjro.parquet")
    router.get(host="archive.org", path="/metadata/datajud-tjro").respond(
        200, json={"files": [{"name": "datajud-capa-tjro.parquet"}]}
    )
    router.get(host="archive.org", path="/download/datajud-tjro/datajud-capa-tjro.parquet").respond(
        200, content=capa_bytes
    )


def _mock_stj_remote(router: respx.MockRouter, fixtures: Path) -> None:
    stj = _stj_parquet(fixtures / "stj-acordaos.parquet")
    router.get(rp._STJ_IA_URL).respond(200, content=stj.read_bytes())


class TestFullReconcileWithoutLocalParquets:
    def test_all_sources_load_via_ia_fallback(
        self, isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        comunicacoes = _comunicacoes_parquet(fixtures / "comunicacoes.parquet")
        catalog = _catalog_parquet(fixtures / "catalog.parquet", [comunicacoes])
        monkeypatch.setattr(rp, "_IA_CATALOG_MANIFEST_URL", str(catalog))

        with respx.mock() as router:
            _mock_stj_remote(router, fixtures)
            _mock_juris_remote(router, fixtures)
            _mock_datajud_remote(router, fixtures)
            stats = rp.reconcile(upload=False)

        assert stats["djen"] == 2  # CNJ_ALL (two pubs collapse) + CNJ_DJEN_DJ
        assert stats["juris"] == 1
        assert stats["stj"] == 1
        assert stats["datajud"] == 2
        assert stats["total"] == 2
        assert stats["multi_fonte"] == 2

        # Output parquet: tem_datajud/tem_juris-style flags actually populated
        con = duckdb.connect()
        try:
            rows = con.execute(
                "SELECT nr_processo, tem_datajud, n_fontes, array_to_string(fontes, '+'), "
                "juris_n_documentos "
                f"FROM read_parquet('{rp._PARQUET_UNIFICADOS}') ORDER BY nr_processo"
            ).fetchall()
        finally:
            con.close()
        assert rows[0] == (CNJ_ALL, True, 4, "djen+juris+stj+datajud", 2)
        assert rows[1] == (CNJ_DJEN_DJ, True, 2, "djen+datajud", None)

        # Coverage report next to the output
        report = json.loads((rp.DATA_DIR / rp._REPORT_NAME).read_text(encoding="utf-8"))
        statuses = {name: src["status"] for name, src in report["sources"].items()}
        assert statuses == {
            "djen": "loaded_remote",
            "juris": "loaded_remote",
            "stj": "loaded_remote",
            "datajud": "loaded_remote",
        }
        assert report["combinations"] == {"djen+juris+stj+datajud": 1, "djen+datajud": 1}
        assert report["validation"]["errors"] == []
        assert report["validation"]["warnings"] == []

    def test_remote_downloads_are_cached_across_runs(self, isolated_dirs: Path) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()

        with respx.mock() as router:
            _mock_datajud_remote(router, fixtures)
            download = router.routes[-1]
            first = rp.fetch_datajud_from_ia()
            second = rp.fetch_datajud_from_ia()

        assert first == second
        assert first[0].exists()
        assert download.call_count == 1  # second run served from cache


class TestUnavailableSources:
    @pytest.fixture
    def unavailable_env(self, isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """DJEN/STJ loaded-but-zero; JURIS/DataJud unavailable on IA."""
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        # Catalog readable but with no comunicacoes rows → djen loaded, zero.
        catalog = _catalog_parquet(fixtures / "catalog.parquet", [])
        monkeypatch.setattr(rp, "_IA_CATALOG_MANIFEST_URL", str(catalog))
        # Local STJ parquet whose CNJ is invalid → stj loaded_local, zero agg rows.
        rp._STJ_PARQUET.parent.mkdir(parents=True, exist_ok=True)
        _stj_parquet(rp._STJ_PARQUET, numero_processo="123")
        return tmp_path

    def _mock_empty_ia(self, router: respx.MockRouter) -> None:
        router.get(host="archive.org", path="/advancedsearch.php").respond(
            200, json={"response": {"docs": []}}
        )
        router.get(host="archive.org", path="/metadata/datajud-tjro").respond(200, json={})

    @pytest.mark.usefixtures("unavailable_env")
    def test_zero_and_unavailable_fails_strict(self) -> None:
        with respx.mock() as router:
            self._mock_empty_ia(router)
            exit_code = rp.main(["--no-upload"])

        assert exit_code == 1
        report = json.loads((rp.DATA_DIR / rp._REPORT_NAME).read_text(encoding="utf-8"))
        statuses = {name: src["status"] for name, src in report["sources"].items()}
        assert statuses["juris"] == "unavailable"
        assert statuses["datajud"] == "unavailable"
        assert statuses["djen"] == "loaded_remote"
        assert statuses["stj"] == "loaded_local"
        errors = report["validation"]["errors"]
        assert len(errors) == 2
        assert any("'juris'" in e for e in errors)
        assert any("'datajud'" in e for e in errors)
        # loaded-but-zero sources warn instead of failing
        warnings = report["validation"]["warnings"]
        assert any("'djen'" in w for w in warnings)
        assert any("'stj'" in w for w in warnings)

    @pytest.mark.usefixtures("unavailable_env")
    def test_strict_disabled_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("RECONCILE_STRICT", "0")
        with respx.mock() as router:
            self._mock_empty_ia(router)
            assert rp.main(["--no-upload"]) == 0

    @pytest.mark.usefixtures("unavailable_env")
    def test_strict_disabled_via_flag(self) -> None:
        with respx.mock() as router:
            self._mock_empty_ia(router)
            assert rp.main(["--no-upload", "--no-strict"]) == 0

    @pytest.mark.usefixtures("unavailable_env")
    def test_unexpected_sources_downgrade_to_warnings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RECONCILE_EXPECTED_SOURCES", "djen,stj")
        with respx.mock() as router:
            self._mock_empty_ia(router)
            assert rp.main(["--no-upload"]) == 0
        report = json.loads((rp.DATA_DIR / rp._REPORT_NAME).read_text(encoding="utf-8"))
        assert report["validation"]["errors"] == []
        assert any("'juris'" in w for w in report["validation"]["warnings"])
        assert any("'datajud'" in w for w in report["validation"]["warnings"])


class TestCorruptedParquetHandling:
    """duckdb.Error / SourceDataError boundaries: bad bytes must not crash the
    whole reconciliation, must not poison the cache, and must not affect
    unrelated sources or unrelated processos.
    """

    def test_corrupted_remote_fallback_makes_source_unavailable_report_written(
        self, isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        comunicacoes = _comunicacoes_parquet(fixtures / "comunicacoes.parquet")
        catalog = _catalog_parquet(fixtures / "catalog.parquet", [comunicacoes])
        monkeypatch.setattr(rp, "_IA_CATALOG_MANIFEST_URL", str(catalog))

        with respx.mock() as router:
            router.get(rp._STJ_IA_URL).respond(200, content=b"not a parquet file at all")
            _mock_juris_remote(router, fixtures)
            _mock_datajud_remote(router, fixtures)
            stats = rp.reconcile(upload=False)  # must not raise, must still write a report

        assert stats["stj"] == 0
        report = json.loads((rp.DATA_DIR / rp._REPORT_NAME).read_text(encoding="utf-8"))
        assert report["sources"]["stj"]["status"] == rp.STATUS_UNAVAILABLE
        assert "not valid parquet" in report["sources"]["stj"]["detail"]
        # other sources are unaffected by STJ's corruption
        assert report["sources"]["djen"]["status"] == rp.STATUS_LOADED_REMOTE
        assert report["sources"]["juris"]["status"] == rp.STATUS_LOADED_REMOTE
        assert report["sources"]["datajud"]["status"] == rp.STATUS_LOADED_REMOTE
        # the corrupt download must never be promoted to the final cache path
        assert not rp._STJ_PARQUET.exists()

    def test_already_corrupted_cache_file_is_not_treated_as_valid(
        self, isolated_dirs: Path
    ) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        cache_path = tmp_path / "cache" / "datajud" / rp._datajud_capa_name("tjro")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"garbage left over from a crashed earlier run")

        with respx.mock() as router:
            _mock_datajud_remote(router, fixtures)
            download_route = router.routes[-1]
            paths = rp.fetch_datajud_from_ia()

        # the invalid cache file was rejected and re-fetched, not reused
        assert download_route.call_count == 1
        assert rp._is_valid_parquet(paths[0])

    def test_null_id_documento_discarded_without_merging_distinct_processos(
        self, isolated_dirs: Path
    ) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        shard = _juris_parquet(
            fixtures / "2024-01-ACORDAO.parquet",
            f"(NULL, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A', 'PJE',"
            " '2024-01-15', 'texto null-1', 'https://juris/null1', '2024-01-31T00:00:00'),"
            f"(1, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A', 'PJE',"
            " '2024-01-15', 'texto um', 'https://juris/1', '2024-01-31T00:00:00'),"
            f"(NULL, '{CNJ_DJEN_DJ}', 'SENTENÇA', 'Apelação', '1a Vara', 'Juiz B', 'PJE',"
            " '2024-02-10', 'texto null-2', 'https://juris/null2', '2024-02-28T00:00:00')",
        )
        with respx.mock() as router:
            router.get(host="archive.org", path="/advancedsearch.php").respond(
                200, json={"response": {"docs": [{"identifier": "tjro-juris-2024"}]}}
            )
            router.get(host="archive.org", path="/metadata/tjro-juris-2024").respond(
                200, json={"files": [{"name": "2024-01-ACORDAO.parquet"}]}
            )
            router.get(
                host="archive.org", path="/download/tjro-juris-2024/2024-01-ACORDAO.parquet"
            ).respond(200, content=shard.read_bytes())

            con = duckdb.connect()
            try:
                load = rp._register_juris(con)
                rows = con.execute(
                    "SELECT nr_processo, id_documento FROM tjro_juris ORDER BY nr_processo"
                ).fetchall()
            finally:
                con.close()

        assert load.status == rp.STATUS_LOADED_REMOTE
        # Both null-id_documento rows are discarded outright — in particular the
        # one for CNJ_DJEN_DJ must NOT survive by merging under a shared NULL
        # key with CNJ_ALL's null row.
        assert rows == [(CNJ_ALL, 1)]

    def test_one_invalid_source_does_not_block_other_valid_sources(
        self, isolated_dirs: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        tmp_path = isolated_dirs
        fixtures = tmp_path / "fixtures"
        fixtures.mkdir()
        comunicacoes = _comunicacoes_parquet(fixtures / "comunicacoes.parquet")
        catalog = _catalog_parquet(fixtures / "catalog.parquet", [comunicacoes])
        monkeypatch.setattr(rp, "_IA_CATALOG_MANIFEST_URL", str(catalog))

        with respx.mock() as router:
            _mock_stj_remote(router, fixtures)
            _mock_datajud_remote(router, fixtures)
            # JURIS's only shard is corrupted — the source becomes unavailable,
            # but DJEN/STJ/DataJud must still load and contribute normally.
            router.get(host="archive.org", path="/advancedsearch.php").respond(
                200, json={"response": {"docs": [{"identifier": "tjro-juris-2024"}]}}
            )
            router.get(host="archive.org", path="/metadata/tjro-juris-2024").respond(
                200, json={"files": [{"name": "2024-01-ACORDAO.parquet"}]}
            )
            router.get(
                host="archive.org", path="/download/tjro-juris-2024/2024-01-ACORDAO.parquet"
            ).respond(200, content=b"definitely not parquet")

            stats = rp.reconcile(upload=False)  # must not raise

        assert stats["juris"] == 0
        assert stats["djen"] == 2
        assert stats["stj"] == 1
        assert stats["datajud"] == 2
        report = json.loads((rp.DATA_DIR / rp._REPORT_NAME).read_text(encoding="utf-8"))
        assert report["sources"]["juris"]["status"] == rp.STATUS_UNAVAILABLE
        assert report["sources"]["djen"]["status"] == rp.STATUS_LOADED_REMOTE
        assert report["sources"]["stj"]["status"] == rp.STATUS_LOADED_REMOTE
        assert report["sources"]["datajud"]["status"] == rp.STATUS_LOADED_REMOTE


class TestValidateCoverage:
    def test_zero_plus_unavailable_expected_is_error(self) -> None:
        sources = {"juris": rp.SourceLoad("juris", rp.STATUS_UNAVAILABLE, "no IA items", rows=0)}
        errors, warnings = rp.validate_coverage(sources, ("juris",))
        assert len(errors) == 1
        assert warnings == []

    def test_zero_plus_loaded_is_warning(self) -> None:
        sources = {"stj": rp.SourceLoad("stj", rp.STATUS_LOADED_LOCAL, "local", rows=0)}
        errors, warnings = rp.validate_coverage(sources, ("stj",))
        assert errors == []
        assert len(warnings) == 1

    def test_unavailable_but_not_expected_is_warning(self) -> None:
        sources = {"juris": rp.SourceLoad("juris", rp.STATUS_UNAVAILABLE, "gone", rows=0)}
        errors, warnings = rp.validate_coverage(sources, ("djen",))
        assert errors == []
        assert len(warnings) == 1

    def test_loaded_with_rows_is_clean(self) -> None:
        sources = {"djen": rp.SourceLoad("djen", rp.STATUS_LOADED_REMOTE, "ok", rows=10)}
        errors, warnings = rp.validate_coverage(sources, ("djen",))
        assert errors == []
        assert warnings == []
