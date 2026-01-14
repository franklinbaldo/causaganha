
import os
import ibis
import pytest
from typer.testing import CliRunner
from pytest_bdd import scenario, given, when, then
from unittest.mock import AsyncMock

from causaganha.config import DB_PATH
from causaganha.cli import app
from causaganha.domain.models import Intimation

runner = CliRunner()

@scenario('../features/data_pipeline.feature', 'Initialize the database')
def test_initialize_database():
    pass

@scenario('../features/data_pipeline.feature', 'Collect data from the API')
def test_collect_data():
    pass


@when("I initialize the database")
def initialize_database():
    result = runner.invoke(app, ["db", "init"])
    assert result.exit_code == 0

@then("the database should be created with the correct schema")
def verify_database_schema():
    assert os.path.exists(DB_PATH)
    con = ibis.duckdb.connect(DB_PATH)
    tables = con.list_tables()
    expected_tables = {
        'pipeline_state',
        'intimations',
        'intimation_lawyers',
        'analysis_results',
        'lawyer_ratings',
    }
    assert expected_tables.issubset(set(tables))

@pytest.fixture
def mock_pje_api(mocker):
    mock_data = [
        Intimation(
            id=1,
            numero_processo="12345-67.2024.8.22.0001",
            data_disponibilizacao="2024-01-01",
            sigla_tribunal="TJRO",
            advogados=[],
            tipo_comunicacao="Intimacao",
            nome_orgao="1. VARA CIVEL",
            texto="Fica V. Sa. intimado para tomar ciencia da sentenca proferida no processo.",
            link="https://example.com/document",
            tipo_documento="Sentenca",
            nome_classe="PROCEDIMENTO COMUM CIVEL",
            codigo_classe="7",
            hash="mock_hash_123",
            status="pending",
        )
    ]

    async def fake_get_intimations(*args, **kwargs):
        return mock_data

    # Patch the PJeAPIClient class in the collect module where it is used
    mocker.patch(
        'causaganha.application.pipeline.collect.PJeAPIClient.get_intimations_by_court',
        new=fake_get_intimations
    )
    mocker.patch(
        'causaganha.application.pipeline.collect.PJeAPIClient.close',
        new=AsyncMock(return_value=None)
    )


@given("the PJe API will return mock data")
def pje_api_will_return_mock_data(mock_pje_api):
    pass

@when("I run the collect command")
def run_collect_command():
    # The database must be initialized before collecting
    runner.invoke(app, ["db", "init"])
    result = runner.invoke(app, ["collect", "--courts", "TJRO"])
    assert result.exit_code == 0

@then("the intimations table should contain the collected data")
def verify_collected_data():
    con = ibis.duckdb.connect(DB_PATH)
    intimations = con.table('intimations').to_pandas()
    assert len(intimations) == 1
    assert intimations.iloc[0]['id'] == 1
    assert intimations.iloc[0]['numero_processo'] == "12345-67.2024.8.22.0001"
