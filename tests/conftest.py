"""Pytest configuration for CausaGanha tests."""

import pytest
from pathlib import Path
import tempfile
import sys
import uuid  # Required for new temp_db logic

# Add src to Python path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_db():
    """
    Provide a temporary, unique path for a DuckDB database file for testing.
    Ensures the file does not exist before yielding the path, so DuckDB can create it.
    The file is cleaned up after the test.
    """
    # Use a unique filename in the system's temporary directory
    temp_dir = Path(tempfile.gettempdir())
    db_file_path = temp_dir / f"test_causaganha_db_{uuid.uuid4()}.duckdb"

    # Ensure no file exists at this path before the test
    if db_file_path.exists():
        try:
            db_file_path.unlink()
        except OSError as e:
            # This might happen if a previous test run failed to clean up and the file is locked
            pytest.skip(
                f"Could not remove pre-existing temp DB file {db_file_path}: {e}"
            )

    yield db_file_path  # DuckDB will create the file when db.connect() is called

    # Cleanup: remove the database file after the test using this fixture is done
    if db_file_path.exists():
        try:
            db_file_path.unlink()
        except OSError:
            # This can happen if the database connection in the test was not properly closed.
            # The test itself should handle closing the DB connection.
            # If it's a persistent issue, tests might need specific teardown logic for their DB instances.
            # For now, we'll log a warning if cleanup fails but not fail the test itself here.
            # (pytest doesn't easily allow logging from fixture teardown to main report)
            print(
                f"Warning: Could not clean up temporary database file {db_file_path} after test."
            )
            pass


@pytest.fixture
def sample_pdf():
    """Provide sample PDF for testing."""
    return Path(__file__).parent / "fixtures" / "sample_pdfs" / "test.pdf"


@pytest.fixture
def sample_data_dir():
    """Provide sample data directory for testing."""
    return Path(__file__).parent / "fixtures" / "sample_data"
