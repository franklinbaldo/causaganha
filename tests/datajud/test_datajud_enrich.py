"""End-to-end tests for the `datajud enrich` CLI against fixtures (no network)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import respx
from typer.testing import CliRunner

from datajud.__main__ import app
from datajud.client import search_endpoint
from datajud.manifest import ManifestDataJud


if TYPE_CHECKING:
    from pathlib import Path


ENDPOINT = search_endpoint("tjro")
CNJ = "00000010220248220001"

runner = CliRunner()


def _source(grau: str, orgao: int, *, movimentos: int = 1) -> dict:
    return {
        "numeroProcesso": CNJ,
        "tribunal": "TJRO",
        "grau": grau,
        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
        "assuntos": [{"codigo": 1234, "nome": "Dano Material"}],
        "orgaoJulgador": {"codigo": orgao, "nome": f"Órgão {orgao}"},
        "sistema": {"codigo": 1, "nome": "PJE"},
        "formato": {"codigo": 1, "nome": "Eletrônico"},
        "nivelSigilo": 0,
        "dataAjuizamento": "20240115103000",
        "dataHoraUltimaAtualizacao": "2026-06-13T09:45:09.000Z",
        "movimentos": [
            {
                "codigo": 26 + i,
                "nome": f"Movimento {i}",
                "dataHora": f"2024-01-{15 + i:02d}T10:00:00Z",
            }
            for i in range(movimentos)
        ],
    }


def _payload(sources: list[dict]) -> dict:
    return {
        "hits": {
            "total": {"value": len(sources), "relation": "eq"},
            "hits": [{"_id": f"id-{i}", "_source": s} for i, s in enumerate(sources)],
        }
    }


def _query(sql: str):
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def test_enrich_with_explicit_cnj_writes_parquets_and_manifest(tmp_path: Path):
    data_dir = tmp_path / "datajud"
    with respx.mock() as router:
        router.post(ENDPOINT).respond(
            200, json=_payload([_source("G1", 111, movimentos=2), _source("G2", 222)])
        )
        result = runner.invoke(
            app,
            [
                "enrich",
                "--tribunal",
                "tjro",
                "--data-dir",
                str(data_dir),
                "--cnj",
                "0000001-02.2024.8.22.0001",
                "--skip-upload",
            ],
        )

    assert result.exit_code == 0, result.output

    capa_path = data_dir / "datajud-capa-tjro.parquet"
    mov_path = data_dir / "datajud-movimentos-tjro.parquet"
    assert capa_path.exists()
    assert mov_path.exists()

    capa_rows = _query(
        f"SELECT grau, data_ajuizamento FROM read_parquet('{capa_path}') ORDER BY grau"
    )
    assert capa_rows == [("G1", "2024-01-15T10:30:00"), ("G2", "2024-01-15T10:30:00")]
    (n_mov,) = _query(f"SELECT COUNT(*) FROM read_parquet('{mov_path}')")[0]
    assert n_mov == 3  # 2 movimentos no G1 + 1 no G2

    manifest = ManifestDataJud.load_local(data_dir / "datajud-manifest.csv")
    entry = manifest.get(CNJ, "tjro")
    assert entry is not None
    assert entry.status == "ok"
    assert entry.docs == 2


def test_enrich_is_incremental_second_run_skips_fresh_cnjs(tmp_path: Path):
    data_dir = tmp_path / "datajud"
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=_payload([_source("G1", 111)]))
        args = [
            "enrich",
            "--data-dir",
            str(data_dir),
            "--cnj",
            CNJ,
            "--skip-upload",
        ]
        first = runner.invoke(app, args)
        second = runner.invoke(app, args)

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert route.call_count == 1  # second run: CNJ is fresh in the manifest
    assert "Nothing to do" in second.output


def test_enrich_cnj_file_and_limit(tmp_path: Path):
    data_dir = tmp_path / "datajud"
    cnj_file = tmp_path / "cnjs.txt"
    cnj_file.write_text(f"{CNJ}\n00000020320248220002\n", encoding="utf-8")

    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=_payload([_source("G1", 111)]))
        result = runner.invoke(
            app,
            [
                "enrich",
                "--data-dir",
                str(data_dir),
                "--cnj-file",
                str(cnj_file),
                "--limit",
                "1",
                "--skip-upload",
            ],
        )

    assert result.exit_code == 0, result.output
    assert route.call_count == 1
    manifest = ManifestDataJud.load_local(data_dir / "datajud-manifest.csv")
    assert len(manifest) == 1  # only the first CNJ (limit) was consulted


def test_enrich_no_cnjs_and_no_sources_fails_nominally(tmp_path: Path, monkeypatch):
    from datajud import service

    # IA fallback download is a urllib call — stub it out (zero real network)
    monkeypatch.setattr(service, "_try_download_unificados", lambda _dir: None)
    result = runner.invoke(
        app,
        [
            "enrich",
            "--data-dir",
            str(tmp_path / "datajud"),
            "--sources-dir",
            str(tmp_path / "empty"),
            "--skip-upload",
        ],
    )
    assert result.exit_code == 1


def test_enrich_reads_cnjs_from_source_parquets(tmp_path: Path):
    sources_dir = tmp_path / "data"
    sources_dir.mkdir()
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT '{CNJ}' AS nr_processo)
        TO '{sources_dir / "processos_unificados.parquet"}' (FORMAT PARQUET)
        """
    )
    con.close()

    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=_payload([_source("G1", 111)]))
        result = runner.invoke(
            app,
            [
                "enrich",
                "--data-dir",
                str(tmp_path / "datajud"),
                "--sources-dir",
                str(sources_dir),
                "--skip-upload",
            ],
        )

    assert result.exit_code == 0, result.output
    assert route.call_count == 1


def test_enrich_reads_cnjs_from_tjro_juris_source_parquet(tmp_path: Path):
    """CNJs from data/tjro-juris/<year>/tjro-juris-<year>.parquet are found.

    That's the real hyphenated layout the crawler writes — not the
    underscore directory a stale glob would look for.
    """
    sources_dir = tmp_path / "data"
    juris_dir = sources_dir / "tjro-juris" / "2024"
    juris_dir.mkdir(parents=True)
    con = duckdb.connect()
    con.execute(
        f"""
        COPY (SELECT '{CNJ}' AS nr_processo)
        TO '{juris_dir / "tjro-juris-2024.parquet"}' (FORMAT PARQUET)
        """
    )
    con.close()

    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=_payload([_source("G1", 111)]))
        result = runner.invoke(
            app,
            [
                "enrich",
                "--data-dir",
                str(tmp_path / "datajud"),
                "--sources-dir",
                str(sources_dir),
                "--skip-upload",
            ],
        )

    assert result.exit_code == 0, result.output
    assert route.call_count == 1  # would be 0 (no CNJs found) before the glob fix


def test_enrich_rate_limit_exhaustion_is_a_nominal_error(tmp_path: Path, monkeypatch):
    from datajud import service

    original = service.DataJudClient
    monkeypatch.setattr(
        service,
        "DataJudClient",
        lambda **kw: original(**{**kw, "backoff_base": 0.0, "max_retries": 1}),
    )
    with respx.mock() as router:
        router.post(ENDPOINT).respond(429)
        result = runner.invoke(
            app,
            [
                "enrich",
                "--data-dir",
                str(tmp_path / "datajud"),
                "--cnj",
                CNJ,
                "--skip-upload",
            ],
        )
    # exhausted retries surface as an error, and no parquet is written
    assert result.exit_code == 1
    assert not (tmp_path / "datajud" / "datajud-capa-tjro.parquet").exists()
