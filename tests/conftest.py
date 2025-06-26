"""Pytest configuration for CausaGanha tests."""
import pytest
from pathlib import Path
import tempfile
import sys

# Add src to Python path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

@pytest.fixture
def temp_db():
    """Provide temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.duckdb', delete=False) as tmp:
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

@pytest.fixture  
def sample_pdf():
    """Provide sample PDF for testing."""
    return Path(__file__).parent / "fixtures" / "sample_pdfs" / "test.pdf"

@pytest.fixture
def sample_data_dir():
    """Provide sample data directory for testing."""
    return Path(__file__).parent / "fixtures" / "sample_data"