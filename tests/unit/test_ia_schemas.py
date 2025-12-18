
import pytest
from datetime import date
from pydantic import ValidationError
from causaganha.ia.schemas import ParquetSchema, LawyerInfo
from causaganha.analysis.models import Outcome

def test_parquet_schema_creation():
    """Test successful creation of a ParquetSchema model."""
    schema = ParquetSchema(
        intimation_id=1,
        process_number="12345",
        tribunal="TJTEST",
        decision_date=date(2024, 1, 1),
        download_url="http://example.com/doc.pdf",
        needs_download=True,
        ia_url="http://archive.org/doc",
        gemini_summary="Summary",
        full_decision_text="Full text",
        outcome=Outcome.WIN,
        winner_lawyers=[LawyerInfo(oab_number="123", oab_state="SP")],
        loser_lawyers=[LawyerInfo(oab_number="456", oab_state="RJ")],
    )
    assert schema.intimation_id == 1
    assert schema.tribunal == "TJTEST"
    assert len(schema.winner_lawyers) == 1


def test_parquet_schema_missing_required_fields():
    """Test that missing required fields raise a validation error."""
    with pytest.raises(ValidationError):
        ParquetSchema(
            intimation_id=1,
            # Missing process_number, tribunal, download_url, needs_download
        )

def test_parquet_schema_optional_fields():
    """Test that optional fields can be None or have default values."""
    schema = ParquetSchema(
        intimation_id=1,
        process_number="12345",
        tribunal="TJTEST",
        download_url="http://example.com/doc.pdf",
        needs_download=False,
    )
    assert schema.decision_date is None
    assert schema.gemini_summary is None
    assert schema.outcome is None
    assert schema.winner_lawyers == []
    assert schema.loser_lawyers == []


def test_lawyer_info_creation():
    """Test the LawyerInfo model."""
    lawyer = LawyerInfo(oab_number="987", oab_state="MG", name="Test Lawyer")
    assert lawyer.name == "Test Lawyer"
