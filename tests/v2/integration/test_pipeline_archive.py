"""Integration tests for the archive pipeline."""

from unittest.mock import AsyncMock, patch

import pytest
from ibis.backends.duckdb import Backend

from causaganha.infrastructure.clients.archive import ArchiveService
from causaganha.infrastructure.clients.document import DocumentService
from causaganha.v2.pipeline.archive import archive_documents


@pytest.fixture
def mock_document_service() -> DocumentService:
    """Mock document service."""
    return AsyncMock(spec=DocumentService)


@pytest.fixture
def mock_archive_service() -> ArchiveService:
    """Mock archive service."""
    service = AsyncMock(spec=ArchiveService)
    service.generate_metadata.return_value = {"title": "Test Document"}
    return service


@pytest.mark.asyncio
async def test_archive_pipeline_success(
    db_connection: Backend,
    mock_document_service: DocumentService,
    mock_archive_service: ArchiveService,
) -> None:
    """Test successful archiving of documents."""
    # 1. Setup: Insert unarchived intimation
    db_connection.con.execute(
        """
        INSERT INTO intimations (
            id, numero_processo, numeroprocessocommascara,
            data_disponibilizacao, sigla_tribunal, id_orgao,
            tipo_comunicacao, nome_orgao, texto, link,
            tipo_documento, nome_classe, codigo_classe,
            hash, status, analyzed
        ) VALUES (
            1, '1234567-89.2024.8.22.0001', '1234567-89.2024.8.22.0001',
            '2024-01-01', 'TJRO', 1,
            'Intimação', 'Vara 1', 'Texto', 'http://example.com/doc.pdf',
            'Decisão', 'Procedimento', 1,
            'hash123', 'NEW', FALSE
        )
        """
    )

    # 2. Mock PreservationService within the pipeline module
    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_cls:
        instance = mock_cls.return_value
        # Mock preserve_document to return a URL
        instance.preserve_document = AsyncMock(
            return_value="https://archive.org/details/test-item"
        )

        # 3. Run Pipeline
        result = await archive_documents(
            mock_document_service,
            mock_archive_service,
            limit=10,
            dry_run=False,
        )

        # 4. Verification
        assert result["status"] == "success"
        assert result["processed"] == 1
        assert result["archived"] == 1
        assert result["failed"] == 0

        # Verify DB update
        t = db_connection.table("intimations")
        row = t.filter(t.id == 1).execute().iloc[0]
        assert row["ia_url"] == "https://archive.org/details/test-item"

        # Verify arguments passed to preservation
        instance.preserve_document.assert_called_once()
        args, _ = instance.preserve_document.call_args
        assert args[0] == "http://example.com/doc.pdf"  # document_url
        assert args[1] == "causaganha-tjro-1"  # item_id


@pytest.mark.asyncio
async def test_archive_pipeline_dry_run(
    db_connection: Backend,
    mock_document_service: DocumentService,
    mock_archive_service: ArchiveService,
) -> None:
    """Test archive pipeline in dry-run mode."""
    # 1. Setup
    db_connection.con.execute(
        """
        INSERT INTO intimations (
            id, numero_processo, numeroprocessocommascara,
            data_disponibilizacao, sigla_tribunal, id_orgao,
            tipo_comunicacao, nome_orgao, texto, link,
            tipo_documento, nome_classe, codigo_classe,
            hash, status, analyzed
        ) VALUES (
            2, '1234567-89.2024.8.22.0001', '1234567-89.2024.8.22.0001',
            '2024-01-01', 'TJRO', 1,
            'Intimação', 'Vara 1', 'Texto', 'http://example.com/doc.pdf',
            'Decisão', 'Procedimento', 1,
            'hash123', 'NEW', FALSE
        )
        """
    )

    # 2. Mock
    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_cls:
        instance = mock_cls.return_value
        # In dry run, preserve_document typically returns None or we can check the dry_run arg
        instance.preserve_document = AsyncMock(return_value=None)

        # 3. Run Pipeline
        result = await archive_documents(
            mock_document_service,
            mock_archive_service,
            limit=10,
            dry_run=True,
        )

        # 4. Verification
        assert result["status"] == "success"
        assert result["processed"] == 1
        assert result["archived"] == 0  # Should not count as archived in stats if URL is None

        # Verify DB was NOT updated
        t = db_connection.table("intimations")
        row = t.filter(t.id == 2).execute().iloc[0]
        assert row["ia_url"] is None

        # Verify dry_run passed to service
        instance.preserve_document.assert_called_once()
        _, kwargs = instance.preserve_document.call_args
        # archive_documents calls as pos args: (url, item_id, metadata, dry_run)
        # So dry_run is the 4th arg
        args = instance.preserve_document.call_args[0]
        assert args[3] is True


@pytest.mark.asyncio
async def test_archive_pipeline_failure(
    db_connection: Backend,
    mock_document_service: DocumentService,
    mock_archive_service: ArchiveService,
) -> None:
    """Test archive pipeline handling failures."""
    # 1. Setup
    db_connection.con.execute(
        """
        INSERT INTO intimations (
            id, numero_processo, numeroprocessocommascara,
            data_disponibilizacao, sigla_tribunal, id_orgao,
            tipo_comunicacao, nome_orgao, texto, link,
            tipo_documento, nome_classe, codigo_classe,
            hash, status, analyzed
        ) VALUES (
            3, '1234567-89.2024.8.22.0001', '1234567-89.2024.8.22.0001',
            '2024-01-01', 'TJRO', 1,
            'Intimação', 'Vara 1', 'Texto', 'http://example.com/doc.pdf',
            'Decisão', 'Procedimento', 1,
            'hash123', 'NEW', FALSE
        )
        """
    )

    # 2. Mock
    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_cls:
        instance = mock_cls.return_value
        # Simulate failure
        instance.preserve_document.side_effect = Exception("Upload error")

        # 3. Run Pipeline
        result = await archive_documents(
            mock_document_service,
            mock_archive_service,
            limit=10,
        )

        # 4. Verification
        assert result["status"] == "success"  # Pipeline continues
        assert result["failed"] == 1
        assert result["archived"] == 0

        # Verify DB not updated
        t = db_connection.table("intimations")
        row = t.filter(t.id == 3).execute().iloc[0]
        assert row["ia_url"] is None
