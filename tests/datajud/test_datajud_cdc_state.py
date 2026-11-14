"""CDC state across ephemeral runners and verifiable publication (#1704, #1706).

A dict stands in for the Internet Archive item: ``archive.upload_file`` writes
into it and ``archive.download_file`` reads from it (``None`` = HTTP 404), so
two "runners" with fresh directories can be chained without any network.
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from datajud import archive, cdc_state
from datajud.cdc import read_parquet_rows, sync_tribunal_cdc


if TYPE_CHECKING:
    from pathlib import Path


CNJ_1 = "00000010220248220001"
CNJ_2 = "00000020320248220002"
CNJ_3 = "00000030420248220003"


def _doc(cnj: str, updated_at: str) -> dict:
    return {
        "numeroProcesso": cnj,
        "grau": "G1",
        "tribunal": "TJRO",
        "classe": {"codigo": 7, "nome": "Procedimento Comum Cível"},
        "assuntos": [],
        "orgaoJulgador": {"codigo": 100, "nome": "1ª Vara Cível"},
        "dataHoraUltimaAtualizacao": updated_at,
        "movimentos": [
            {"codigo": 26, "nome": "Distribuição", "dataHora": updated_at},
        ],
    }


class FakeArchive:
    """In-memory IA item with optional failure injection."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.upload_order: list[str] = []
        self.fail_upload: set[str] = set()
        self.download_error = False

    def upload_file(self, path: Path, _tribunal: str, _key: str, _secret: str) -> bool:
        if any(path.name.startswith(prefix) for prefix in self.fail_upload):
            return False
        self.files[path.name] = path.read_bytes()
        self.upload_order.append(path.name)
        return True

    def download_file(self, name: str, _tribunal: str, **_kwargs: object) -> bytes | None:
        if self.download_error:
            msg = "simulated transport failure"
            raise OSError(msg)
        return self.files.get(name)


@pytest.fixture
def fake_ia(monkeypatch: pytest.MonkeyPatch) -> FakeArchive:
    fake = FakeArchive()
    monkeypatch.setattr(archive, "upload_file", fake.upload_file)
    monkeypatch.setattr(archive, "download_file", fake.download_file)
    return fake


def _client(pages: list[tuple[list[dict], list]], seen_cursor: list) -> MagicMock:
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    async def iterate(**kwargs: object):
        seen_cursor.append(kwargs.get("search_after"))
        for page in pages:
            yield page

    client.iter_updated_since = iterate
    return client


async def _run(root: Path, pages: list, seen: list, **kwargs: object):
    """One ephemeral runner: brand-new directories under *root*."""
    return await sync_tribunal_cdc(
        "tjro",
        base_dir=root / "cdc",
        canonical_dir=root / "canonical",
        daily_dir=root / "daily",
        index_dir=root / "index",
        client=_client(pages, seen),
        pause_between_pages=0.0,
        **kwargs,
    )


PUBLISH = {"upload": True, "restore_remote": True, "ia_key": "k", "ia_secret": "s"}


async def test_two_clean_runners_keep_data_and_advance_cursor(tmp_path: Path, fake_ia: FakeArchive):
    seen1: list = []
    res1 = await _run(
        tmp_path / "runner1",
        [([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1])],
        seen1,
        **PUBLISH,
    )
    assert res1.restore_status == "bootstrap"
    assert res1.checkpoint.status == "published"
    assert seen1 == [None]

    seen2: list = []
    res2 = await _run(
        tmp_path / "runner2",
        [([_doc(CNJ_2, "2026-03-02T10:00:00Z")], [2, CNJ_2])],
        seen2,
        **PUBLISH,
    )
    assert res2.restore_status == "restored"
    # The second runner resumed from the first runner's published cursor ...
    assert seen2 == [[1, CNJ_1]]
    assert res2.checkpoint.last_sort_key == [2, CNJ_2]
    assert res2.checkpoint.total_documents == 2
    # ... and published a canonical that still holds the first runner's CNJ.
    capa = fake_ia.files[archive.capa_parquet_name("tjro")]
    path = tmp_path / "capa.parquet"
    path.write_bytes(capa)
    assert {r["numero_processo"] for r in read_parquet_rows(path)} == {CNJ_1, CNJ_2}


async def test_bundle_is_published_last(tmp_path: Path, fake_ia: FakeArchive):
    await _run(tmp_path, [([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1])], [], **PUBLISH)
    order = fake_ia.upload_order
    assert order[0].startswith("tjro_") and order[0].endswith(".zip")
    assert order[-1] == cdc_state.bundle_name("tjro")
    assert set(order[1:-1]) == {
        archive.capa_parquet_name("tjro"),
        archive.movimentos_parquet_name("tjro"),
        cdc_state.index_name("tjro"),
    }


@pytest.mark.parametrize(
    "failing",
    ["tjro_", "datajud-capa-", "datajud-movimentos-", "indice_processos_", "datajud-cdc-state-"],
)
async def test_failure_at_any_stage_raises_and_keeps_previous_cursor(
    tmp_path: Path, fake_ia: FakeArchive, failing: str
):
    await _run(
        tmp_path / "first", [([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1])], [], **PUBLISH
    )
    published_bundle = fake_ia.files[cdc_state.bundle_name("tjro")]

    fake_ia.fail_upload = {failing}
    with pytest.raises(cdc_state.CdcStateError, match="failed to publish"):
        await _run(
            tmp_path / "second",
            [([_doc(CNJ_2, "2026-03-02T10:00:00Z")], [2, CNJ_2])],
            [],
            **PUBLISH,
        )

    # The commit point did not move: a third runner restarts from the first cursor.
    assert fake_ia.files[cdc_state.bundle_name("tjro")] == published_bundle
    fake_ia.fail_upload = set()
    seen: list = []
    res = await _run(
        tmp_path / "third",
        [([_doc(CNJ_2, "2026-03-02T10:00:00Z")], [2, CNJ_2])],
        seen,
        **PUBLISH,
    )
    assert seen == [[1, CNJ_1]]
    assert res.checkpoint.status == "published"


async def test_upload_without_credentials_is_an_error(tmp_path: Path, fake_ia: FakeArchive):
    with pytest.raises(cdc_state.CdcStateError, match="credentials"):
        await _run(tmp_path, [], [], upload=True, ia_key="", ia_secret="")
    assert fake_ia.upload_order == []


async def test_unreachable_remote_is_not_bootstrap(tmp_path: Path, fake_ia: FakeArchive):
    fake_ia.download_error = True
    with pytest.raises(cdc_state.CdcStateError, match="failed to download"):
        await _run(tmp_path, [], [], **PUBLISH)


async def test_corrupted_bundle_fails_closed(tmp_path: Path, fake_ia: FakeArchive):
    await _run(tmp_path / "a", [([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1])], [], **PUBLISH)
    name = cdc_state.bundle_name("tjro")
    original = zipfile.ZipFile(io.BytesIO(fake_ia.files[name]))
    tampered = io.BytesIO()
    with zipfile.ZipFile(tampered, "w") as out:
        for item in original.namelist():
            data = original.read(item)
            if item == cdc_state.CHECKPOINT_NAME:
                data = data.replace(b'"published"', b'"tampered"')
            out.writestr(item, data)
    fake_ia.files[name] = tampered.getvalue()

    with pytest.raises(cdc_state.CdcStateError, match="checksum mismatch"):
        await _run(tmp_path / "b", [], [], **PUBLISH)


async def test_first_run_seeds_from_published_canonical(tmp_path: Path, fake_ia: FakeArchive):
    """Without a bundle, already-published loose Parquets must not be shrunk."""
    # Simulate a legacy publication (pre-bundle) holding CNJ_1.
    legacy = tmp_path / "legacy"
    await _run(legacy, [([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1])], [], **PUBLISH)
    del fake_ia.files[cdc_state.bundle_name("tjro")]

    res = await _run(
        tmp_path / "fresh", [([_doc(CNJ_3, "2026-03-03T10:00:00Z")], [3, CNJ_3])], [], **PUBLISH
    )
    assert res.restore_status == "legacy"
    path = tmp_path / "capa.parquet"
    path.write_bytes(fake_ia.files[archive.capa_parquet_name("tjro")])
    assert {r["numero_processo"] for r in read_parquet_rows(path)} == {CNJ_1, CNJ_3}


async def test_half_published_canonical_is_an_error(tmp_path: Path, fake_ia: FakeArchive):
    fake_ia.files[archive.capa_parquet_name("tjro")] = b"x"
    with pytest.raises(cdc_state.CdcStateError, match="incomplete"):
        await _run(tmp_path, [], [], **PUBLISH)


async def test_time_budget_stops_stream_and_still_publishes(tmp_path: Path, fake_ia: FakeArchive):
    pages = [
        ([_doc(CNJ_1, "2026-03-01T10:00:00Z")], [1, CNJ_1]),
        ([_doc(CNJ_2, "2026-03-02T10:00:00Z")], [2, CNJ_2]),
    ]
    res = await _run(tmp_path, pages, [], max_duration_s=0, **PUBLISH)
    assert res.stream_exhausted is False
    assert res.documents_streamed == 1
    assert res.checkpoint.last_sort_key == [1, CNJ_1]
    assert res.checkpoint.status == "published"
