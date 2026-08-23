"""Regression tests for durable DataJud state across ephemeral runners."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest

from datajud import archive, service, state
from datajud.manifest import ManifestDataJud
from datajud.models import ProcessoCapa


if TYPE_CHECKING:
    from pathlib import Path


CNJ_A = "00000010220248220001"
CNJ_B = "00000020320248220002"


def _source(cnj: str, *, orgao: int) -> dict:
    return {
        "numeroProcesso": cnj,
        "tribunal": "TJRO",
        "grau": "G1",
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
                "codigo": 26,
                "nome": "Movimento",
                "dataHora": "2024-01-15T10:00:00Z",
            }
        ],
    }


def _install_remote(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    remote: dict[str, bytes] = {}

    def download_file(file_name: str, _tribunal: str) -> bytes | None:
        return remote.get(file_name)

    def upload_file(
        file_path: Path,
        _tribunal: str,
        _ia_key: str,
        _ia_secret: str,
    ) -> bool:
        remote[file_path.name] = file_path.read_bytes()
        return True

    monkeypatch.setattr(archive, "download_file", download_file)
    monkeypatch.setattr(archive, "upload_file", upload_file)
    return remote


def _install_fetch(monkeypatch: pytest.MonkeyPatch, calls: list[list[str]]) -> None:
    async def fetch_capas(cnjs: list[str], _tribunal: str, _batch_size: int) -> list[ProcessoCapa]:
        calls.append(list(cnjs))
        return [
            ProcessoCapa.from_source(_source(cnj, orgao=index + 100))
            for index, cnj in enumerate(cnjs)
        ]

    monkeypatch.setattr(service, "fetch_capas", fetch_capas)


def _run(data_dir: Path) -> service.EnrichResult:
    return service.enrich(
        "tjro",
        data_dir,
        data_dir.parent / "sources",
        [CNJ_A, CNJ_B],
        None,
        1,
        30,
        50,
        skip_upload=False,
        ia_key=data_dir.name,
        ia_secret=data_dir.parent.name,
    )


def _capa_cnjs(path: Path) -> list[str]:
    con = duckdb.connect()
    try:
        rows = con.execute(
            f"SELECT DISTINCT numero_processo FROM read_parquet('{path}') ORDER BY 1"
        ).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def test_two_clean_runners_restore_then_extend_same_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _install_remote(monkeypatch)
    calls: list[list[str]] = []
    _install_fetch(monkeypatch, calls)

    run_a = _run(tmp_path / "runner-a" / "datajud")
    assert run_a.status == "done"
    assert run_a.restore_status == "bootstrap"
    assert calls == [[CNJ_A]]
    assert state.bundle_name("tjro") in remote

    run_b = _run(tmp_path / "runner-b" / "datajud")
    assert run_b.status == "done"
    assert run_b.restore_status == "restored"
    assert calls == [[CNJ_A], [CNJ_B]]

    clean = tmp_path / "runner-c" / "datajud"
    restored = state.restore_remote_state(clean, "tjro")
    assert restored.status == "restored"
    assert restored.generation == run_b.generation

    manifest = ManifestDataJud.load_local(clean / service.MANIFEST_NAME)
    assert len(manifest) == 2
    assert manifest.get(CNJ_A, "tjro") is not None
    assert manifest.get(CNJ_B, "tjro") is not None
    assert _capa_cnjs(clean / archive.capa_parquet_name("tjro")) == [CNJ_A, CNJ_B]


def test_failed_publication_does_not_advance_authoritative_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _install_remote(monkeypatch)
    calls: list[list[str]] = []
    _install_fetch(monkeypatch, calls)

    first = _run(tmp_path / "runner-a" / "datajud")
    assert first.status == "done"
    bundle_file = state.bundle_name("tjro")
    committed = remote[bundle_file]

    def fail_movimentos(
        file_path: Path,
        _tribunal: str,
        _ia_key: str,
        _ia_secret: str,
    ) -> bool:
        if file_path.name == archive.movimentos_parquet_name("tjro"):
            return False
        remote[file_path.name] = file_path.read_bytes()
        return True

    monkeypatch.setattr(archive, "upload_file", fail_movimentos)
    failed = _run(tmp_path / "runner-b" / "datajud")
    assert failed.status == "upload_error"
    assert failed.error == archive.movimentos_parquet_name("tjro")
    assert remote[bundle_file] == committed

    clean = tmp_path / "runner-c" / "datajud"
    restored = state.restore_remote_state(clean, "tjro")
    assert restored.status == "restored"
    manifest = ManifestDataJud.load_local(clean / service.MANIFEST_NAME)
    assert len(manifest) == 1
    assert manifest.get(CNJ_A, "tjro") is not None
    assert manifest.get(CNJ_B, "tjro") is None
    assert _capa_cnjs(clean / archive.capa_parquet_name("tjro")) == [CNJ_A]


def test_legacy_bootstrap_requires_both_canonical_parquets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _install_remote(monkeypatch)
    remote[archive.capa_parquet_name("tjro")] = b"capa-only"

    with pytest.raises(state.RemoteStateError, match="legacy DataJud state is incomplete"):
        state.restore_remote_state(tmp_path / "datajud", "tjro")


def test_corrupted_bundle_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote = _install_remote(monkeypatch)
    remote[state.bundle_name("tjro")] = b"not-a-zip"

    with pytest.raises(state.RemoteStateError, match="invalid DataJud state bundle"):
        state.restore_remote_state(tmp_path / "datajud", "tjro")
