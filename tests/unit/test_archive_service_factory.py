import asyncio
from pathlib import Path

from causaganha.services.archive import LocalArchiveService, create_archive_service


def test_create_archive_service_defaults_to_local(monkeypatch) -> None:
    monkeypatch.delenv("IA_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IA_SECRET_KEY", raising=False)
    service = create_archive_service()
    assert isinstance(service, LocalArchiveService)


def test_local_archive_service_uploads(tmp_path) -> None:
    svc = LocalArchiveService(archive_root=tmp_path / "archive")
    source = tmp_path / "x.pdf"
    source.write_bytes(b"%PDF-1.4 test")

    url = asyncio.run(svc.upload_file(source, "item-1", metadata={"x": "y"}))

    assert url is not None
    dest = Path(url)
    assert dest.exists()
    assert dest.read_bytes() == b"%PDF-1.4 test"
