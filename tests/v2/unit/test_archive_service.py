from pathlib import Path

import pytest

from causaganha.services.archive import LocalArchiveService


@pytest.fixture
def mock_archive_root(tmp_path: Path) -> Path:
    return tmp_path / "archive"

@pytest.fixture
def local_archive_service(mock_archive_root: Path) -> LocalArchiveService:
    return LocalArchiveService(archive_root=mock_archive_root)

@pytest.mark.asyncio
async def test_upload_file_uses_metadata_structure(
    local_archive_service: LocalArchiveService,
    mock_archive_root: Path,
    tmp_path: Path,
) -> None:
    """Test that upload_file stores file in Tribunal/Year/Month/ structure."""
    # Create a dummy file
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"dummy content")

    item_id = "causaganha-tjro-123"
    metadata = {
        "sigla_tribunal": "TJRO",
        "data_disponibilizacao": "2023-05-20", # Year 2023, Month 05
        "numero_processo": "12345",
    }

    # Call upload
    saved_path_str = await local_archive_service.upload_file(file_path, item_id, metadata)

    assert saved_path_str is not None
    saved_path = Path(saved_path_str)

    expected_path = mock_archive_root / "TJRO" / "2023" / "05" / item_id / "test.pdf"

    # Verify the file exists at the expected location
    assert saved_path == expected_path
    assert saved_path.exists()
    assert saved_path.read_bytes() == b"dummy content"

@pytest.mark.asyncio
async def test_upload_file_fallback_no_metadata(
    local_archive_service: LocalArchiveService,
    mock_archive_root: Path,
    tmp_path: Path,
) -> None:
    """Test fallback when metadata is missing."""
    file_path = tmp_path / "test.pdf"
    file_path.write_bytes(b"dummy content")

    item_id = "causaganha-unknown-123"

    # Empty metadata
    saved_path_str = await local_archive_service.upload_file(file_path, item_id, {})

    saved_path = Path(saved_path_str)

    # Should fall back to root / item_id / filename
    expected_path = mock_archive_root / item_id / "test.pdf"

    assert saved_path == expected_path
    assert saved_path.exists()
