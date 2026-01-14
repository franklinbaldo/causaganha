
import os
import ibis
from typer.testing import CliRunner
from pytest_bdd import scenario, given, when, then

from causaganha.config import DB_PATH
from causaganha.cli import app

runner = CliRunner()

@scenario('../features/data_pipeline.feature', 'Initialize the database')
def test_initialize_database():
    pass

@given("the system is in a clean state")
def clean_state():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

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
