"""TDD tests for archive functionality with repository abstractions (RED phase)."""

from datetime import datetime

import pytest

from causaganha.domain.models import Intimation
from causaganha.infrastructure.storage.connection import get_connection
from causaganha.infrastructure.storage.repositories.intimation import IntimationRepository
from causaganha.infrastructure.storage.schema import create_schema


@pytest.fixture
def test_db_connection(tmp_path):
    """Create a test database connection."""
    db_path = tmp_path / "test.duckdb"
    con = get_connection(str(db_path))
    create_schema(con)
    yield con
    con.con.close()


@pytest.fixture
def repository(test_db_connection):
    """Create a repository with test connection."""
    return IntimationRepository(test_db_connection)


@pytest.fixture
def sample_intimation():
    """Create a sample intimation for testing."""
    return Intimation(
        id=1,
        numero_processo="1234567-89.2024.8.22.0001",
        data_disponibilizacao=datetime(2024, 1, 15),
        sigla_tribunal="TJRO",
        tipo_comunicacao="Intimação",
        nome_orgao="1ª Vara Cível",
        texto="Test intimation",
        link="http://example.com/doc.pdf",
        tipo_documento="PDF",
        nome_classe="Procedimento Comum",
        codigo_classe="318",
        hash="abc123",
        status="pending",
    )


class TestRepositoryArchiveOperations:
    """Test that repository can perform archive operations (TDD)."""

    @pytest.mark.asyncio
    async def test_can_mark_intimation_as_archived(self, repository, sample_intimation) -> None:
        """Repository should be able to mark an intimation as archived."""
        # Arrange - Store an intimation
        await repository.store_intimations([sample_intimation])

        # Act - Mark as archived
        ia_url = "https://archive.org/details/test-1"
        await repository.mark_as_archived(str(sample_intimation.id), ia_url)

        # Assert - Should not raise exception
        # Behavior: marking as archived succeeds

    @pytest.mark.asyncio
    async def test_get_unarchived_intimations_returns_only_unarchived(self, repository) -> None:
        """get_unarchived_intimations should return only intimations not yet archived."""
        # Arrange - Store mix of archived and unarchived
        intimation1 = Intimation(
            id=10,
            numero_processo="1111111-89.2024.8.22.0001",
            data_disponibilizacao=datetime(2024, 1, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara",
            texto="Test",
            link="http://example.com/1.pdf",
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="hash1",
            status="pending",
        )

        intimation2 = Intimation(
            id=11,
            numero_processo="2222222-89.2024.8.22.0002",
            data_disponibilizacao=datetime(2024, 1, 16),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara",
            texto="Test",
            link="http://example.com/2.pdf",
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="hash2",
            status="pending",
        )

        await repository.store_intimations([intimation1, intimation2])

        # Mark one as archived
        await repository.mark_as_archived("11", "https://archive.org/details/test-11")

        # Act - Get unarchived
        unarchived = await repository.get_unarchived_intimations(limit=10)

        # Assert - Should only get the unarchived one
        assert len(unarchived) == 1
        assert unarchived[0]["id"] == 10

    @pytest.mark.asyncio
    async def test_get_unarchived_excludes_intimations_without_links(self, repository) -> None:
        """get_unarchived_intimations should exclude intimations without download links."""
        # Arrange
        intimation_with_link = Intimation(
            id=20,
            numero_processo="3333333-89.2024.8.22.0020",
            data_disponibilizacao=datetime(2024, 1, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara",
            texto="With link",
            link="http://example.com/20.pdf",
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="hash20",
            status="pending",
        )

        intimation_without_link = Intimation(
            id=21,
            numero_processo="4444444-89.2024.8.22.0021",
            data_disponibilizacao=datetime(2024, 1, 16),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara",
            texto="No link",
            link=None,  # No download link
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="hash21",
            status="pending",
        )

        await repository.store_intimations([intimation_with_link, intimation_without_link])

        # Act
        unarchived = await repository.get_unarchived_intimations(limit=10)

        # Assert - Should only return the one with a link
        assert len(unarchived) == 1
        assert unarchived[0]["id"] == 20

    @pytest.mark.asyncio
    async def test_marking_as_archived_prevents_it_from_appearing_in_unarchived(self, repository) -> None:
        """After marking as archived, intimation should not appear in get_unarchived_intimations."""
        # Arrange
        intimation = Intimation(
            id=30,
            numero_processo="5555555-89.2024.8.22.0030",
            data_disponibilizacao=datetime(2024, 1, 15),
            sigla_tribunal="TJRO",
            tipo_comunicacao="Intimação",
            nome_orgao="Vara",
            texto="Test",
            link="http://example.com/30.pdf",
            tipo_documento="PDF",
            nome_classe="Comum",
            codigo_classe="318",
            hash="hash30",
            status="pending",
        )

        await repository.store_intimations([intimation])

        # Verify it appears in unarchived before archiving
        unarchived_before = await repository.get_unarchived_intimations(limit=10)
        assert len(unarchived_before) == 1

        # Act - Mark as archived
        await repository.mark_as_archived("30", "https://archive.org/details/test-30")

        # Assert - Should no longer appear in unarchived
        unarchived_after = await repository.get_unarchived_intimations(limit=10)
        assert len(unarchived_after) == 0

    @pytest.mark.asyncio
    async def test_respects_limit_parameter(self, repository) -> None:
        """get_unarchived_intimations should respect the limit parameter."""
        # Arrange - Create 5 unarchived intimations
        intimations = [
            Intimation(
                id=40 + i,
                numero_processo=f"{6000000 + i}-89.2024.8.22.0001",
                data_disponibilizacao=datetime(2024, 1, 15),
                sigla_tribunal="TJRO",
                tipo_comunicacao="Intimação",
                nome_orgao="Vara",
                texto=f"Test {i}",
                link=f"http://example.com/{40 + i}.pdf",
                tipo_documento="PDF",
                nome_classe="Comum",
                codigo_classe="318",
                hash=f"hash{40 + i}",
                status="pending",
            )
            for i in range(5)
        ]

        await repository.store_intimations(intimations)

        # Act - Request only 3
        unarchived = await repository.get_unarchived_intimations(limit=3)

        # Assert
        assert len(unarchived) <= 3
