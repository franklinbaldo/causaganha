from datetime import date
from unittest.mock import AsyncMock

import pytest
from ibis import BaseBackend

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.api.client import PJeAPIClient
from causaganha.api.schemas import Intimation as APIIntimation
from causaganha.domain.models import Intimation as DomainIntimation
from causaganha.domain.models import Lawyer, Party
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.archive import ArchiveService
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema


# Realistic minimal dataset for E2E testing
SAMPLE_INTIMATIONS_DATA = {
    "count": 5,
    "items": [
        {
            "id": 1001,
            "data_disponibilizacao": "2025-01-07",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "2ª Vara Cível",
            "idOrgao": 42457,
            "texto": "PODER JUDICIÁRIO... SENTENÇA PROCEDENTE...",
            "numero_processo": "70127110520238220007",
            "meio": "D",
            "link": "https://pjepg.tjro.jus.br/doc/1001",
            "tipoDocumento": "Sentença",
            "nomeClasse": "CUMPRIMENTO DE SENTENçA",
            "codigoClasse": "156",
            "numeroComunicacao": 1,
            "ativo": True,
            "hash": "hash1001",
            "datadisponibilizacao": "07/01/2025",
            "meiocompleto": "Diário de Justiça Eletrônico Nacional",
            "numeroprocessocommascara": "7012711-05.2023.8.22.0007",
            "destinatarios": [
                {"polo": "P", "comunicacao_id": 1001, "nome": "BANCO DO BRASIL SA"},
            ],
            "destinatarioadvogados": [
                {
                    "advogado": {
                        "id": 9003,
                        "nome": "LAWYER WINNER",
                        "numero_oab": "12345",
                        "uf_oab": "RO",
                    },
                },
            ],
        },
        {
            "id": 1002,
            "data_disponibilizacao": "2025-01-07",
            "siglaTribunal": "TJRO",
            "tipoComunicacao": "Intimação",
            "nomeOrgao": "1ª Vara Cível",
            "idOrgao": 800,
            "texto": "DECISÃO... INDEFERIDO...",
            "numero_processo": "70043575120248220008",
            "meio": "D",
            "link": "https://pjepg.tjro.jus.br/doc/1002",
            "tipoDocumento": "Decisão",
            "nomeClasse": "PROCEDIMENTO COMUM",
            "codigoClasse": "280",
            "numeroComunicacao": 2,
            "ativo": True,
            "hash": "hash1002",
            "datadisponibilizacao": "07/01/2025",
            "meiocompleto": "Diário de Justiça Eletrônico Nacional",
            "numeroprocessocommascara": "7004357-51.2024.8.22.0008",
            "destinatarios": [{"polo": "A", "comunicacao_id": 1002, "nome": "AUTHOR"}],
            "destinatarioadvogados": [
                {
                    "advogado": {
                        "id": 9504,
                        "nome": "LAWYER LOSER",
                        "numero_oab": "54321",
                        "uf_oab": "SP",
                    },
                },
            ],
        },
        # Add a few more to test batching if needed, but 2 is sufficient for lifecycle logic
    ],
}


@pytest.fixture
def db_connection() -> BaseBackend:
    """Creates a temporary in-memory DuckDB connection with schema."""
    con = get_connection(":memory:")
    create_schema(con)
    return con


@pytest.fixture
def repository(db_connection: BaseBackend) -> IntimationRepository:
    """Returns an IntimationRepository using the temp DB."""
    return IntimationRepository(db_connection)


@pytest.fixture
def mock_client() -> AsyncMock:
    """Mocks PJeAPIClient to return sample data."""
    client = AsyncMock(spec=PJeAPIClient)

    domain_objects = []

    def map_to_domain(api_obj: APIIntimation) -> DomainIntimation:
        advogados = [
            Lawyer(
                id=d.advogado.id,
                nome=d.advogado.nome,
                numero_oab=d.advogado.numero_oab,
                uf_oab=d.advogado.uf_oab,
            )
            for d in api_obj.destinatarioadvogados
        ]

        partes = [Party(nome=p.nome, polo=p.polo) for p in api_obj.destinatarios]

        return DomainIntimation(
            id=api_obj.id,
            numero_processo=api_obj.numero_processo,
            numero_processo_formatado=api_obj.numeroprocessocommascara,
            data_disponibilizacao=date.fromisoformat(api_obj.data_disponibilizacao),
            sigla_tribunal=api_obj.sigla_tribunal,
            tipo_comunicacao=api_obj.tipo_comunicacao,
            nome_orgao=api_obj.nome_orgao,
            texto=api_obj.texto,
            link=api_obj.link,
            tipo_documento=api_obj.tipo_documento,
            nome_classe=api_obj.nome_classe,
            codigo_classe=api_obj.codigo_classe,
            hash=api_obj.hash,
            status=None,
            advogados=advogados,
            partes=partes,
        )

    for item in SAMPLE_INTIMATIONS_DATA["items"]:
        if "id" in item:
            # Create API object first to handle aliasing
            api_obj = APIIntimation(**item)
            # Map to domain
            domain_obj = map_to_domain(api_obj)
            domain_objects.append(domain_obj)

    client.get_intimations_by_court.return_value = domain_objects
    return client


@pytest.fixture
def mock_doc_service() -> AsyncMock:
    """Mocks DocumentService to return fake PDF bytes."""
    service = AsyncMock(spec=DocumentService)
    service.download_pdf.return_value = b"%PDF-1.4 Fake PDF Content"
    return service


@pytest.fixture
def mock_archive_service() -> AsyncMock:
    """Mocks ArchiveService."""
    service = AsyncMock(spec=ArchiveService)
    # Mock upload_file to return a fake IA URL
    service.upload_file.return_value = "https://archive.org/details/fake-item-id"
    service.generate_metadata.return_value = {"title": "Fake Title"}
    return service


@pytest.fixture
def mock_analyzer() -> AsyncMock:
    """Mocks DecisionAnalyzer to return deterministic results."""
    analyzer = AsyncMock()

    # Define a successful analysis result
    success_result = DecisionAnalysis(
        outcome=Outcome.WIN,
        summary="Judge ruled in favor.",
        judge_name="Judge Dredd",
        confidence_score=0.95,
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Alice",
        loser_lawyer_oab="54321",
        loser_lawyer_state="SP",
        loser_party_name="Bob Corp",
        decision_type="Merit",
        decision_reasoning="Reasoning...",
    )

    analyzer.analyze_decision.return_value = success_result
    return analyzer


@pytest.mark.asyncio
async def test_full_lifecycle(
    repository: IntimationRepository,
    mock_client: AsyncMock,
    mock_doc_service: AsyncMock,
    mock_archive_service: AsyncMock,
    mock_analyzer: AsyncMock,
) -> None:
    """Verifies the complete lifecycle.

    Sequence: Collect -> Analyze -> Score -> Archive.
    """
    # --- Step 1: Collection ---
    await run_collection(
        repository=repository,
        client=mock_client,
        start_date="2025-01-01",
        end_date="2025-01-02",
        courts=["TJRO"],
    )

    # Verify Collection
    intimations = await repository.get_all_intimations(limit=1000)
    assert len(intimations) == 2, "Collection should have stored 2 items"
    assert intimations[0]["sigla_tribunal"] == "TJRO"

    # --- Step 2: Analysis ---
    # We run analysis before archiving to ensure we have metadata/results if needed
    await run_analysis(
        repository=repository,
        doc_service=mock_doc_service,
        analyzer=mock_analyzer,
        limit=5,
        batch_size=10,
    )

    # Verify Analysis
    results = await repository.get_unscored_analyses(limit=100)
    assert len(results) == 2, "Analysis step should have stored results"
    assert results[0]["outcome"] == "WIN"
    assert results[0]["winner_lawyer_oab"] == "12345"

    # Verify intimation is marked as analyzed
    analyzed_items = await repository.get_all_intimations(limit=1000)
    analyzed_count = sum(1 for i in analyzed_items if i.get("analyzed"))
    assert analyzed_count == 2, "Intimations should be marked as analyzed"

    # --- Step 3: Scoring ---
    await run_scoring(repository=repository, limit=100)

    # Verify Scoring
    ratings = await repository.get_lawyer_ratings([("12345", "RO"), ("54321", "SP")])
    assert len(ratings) == 2, "Should have ratings for both winner and loser"

    winner = next(r for r in ratings if r["oab_number"] == "12345")
    loser = next(r for r in ratings if r["oab_number"] == "54321")

    # Both cases analyzed returned the same winner/loser
    assert winner["wins"] == 2
    assert loser["losses"] == 2
    assert winner["total_cases"] == 2

    # --- Step 4: Archive ---
    await run_archive(
        repository=repository,
        doc_service=mock_doc_service,
        archive_service=mock_archive_service,
        limit=5,
        dry_run=False,
    )

    # Verify Archive
    archived_items = await repository.get_all_intimations(limit=1000)
    archived_count = sum(1 for i in archived_items if i.get("ia_url"))
    assert archived_count == 2, "Archive step should have updated ia_url for all items"
