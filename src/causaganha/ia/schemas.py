"""Reusable Pydantic schemas for data exchange with the orchestrator.

This module defines the data structures that will be used to create Parquet files
for upload to the Internet Archive (IA). The orchestrator function will consume
these Parquet files to perform batch analysis with Gemini.
"""
from datetime import date

from pydantic import BaseModel, Field

from causaganha.analysis.models import Outcome


class LawyerInfo(BaseModel):
    """Represents a lawyer involved in a case."""
    oab_number: str | None = Field(None, description="OAB number of the lawyer.")
    oab_state: str | None = Field(None, description="State of the lawyer's OAB.")
    name: str | None = Field(None, description="Name of the lawyer.")


class ParquetSchema(BaseModel):
    """Defines the schema for Parquet files uploaded to the Internet Archive.

    This schema combines metadata from the `Intimation` and `DecisionAnalysis`
    models to provide a complete record for each case.

    Example:
        .. code-block:: python

            from datetime import date
            from causaganha.ia.schemas import ParquetSchema, LawyerInfo, Outcome

            manifest_entry = ParquetSchema(
                intimation_id=12345,
                process_number="0001-01.2024.8.22.0001",
                tribunal="TJRO",
                decision_date=date(2024, 1, 15),
                download_url="http://example.com/document.pdf",
                needs_download=True,
                # Fields from Gemini analysis would be populated after processing
                gemini_summary="The court denied the appeal.",
                outcome=Outcome.LOSS,
                winner_lawyers=[LawyerInfo(oab_number="123", oab_state="RO")],
                loser_lawyers=[LawyerInfo(oab_number="456", oab_state="RO")],
            )
    """
    # Core Intimation Metadata
    intimation_id: int = Field(..., description="Unique ID for the intimation.")
    process_number: str = Field(..., description="The case number.")
    tribunal: str = Field(..., description="The court that issued the decision (e.g., 'TJRO').")
    decision_date: date | None = Field(None, description="The date of the decision.")
    download_url: str = Field(..., description="URL to the original PDF document.")
    needs_download: bool = Field(..., description="Flag indicating if the PDF needs to be downloaded.")
    ia_url: str | None = Field(None, description="URL of the document on the Internet Archive.")

    # Gemini Analysis Results
    gemini_summary: str | None = Field(None, description="Summary of the decision from Gemini.")
    full_decision_text: str | None = Field(None, description="The full text of the decision (acórdão).")
    outcome: Outcome | None = Field(None, description="The outcome of the case (WIN, LOSS, etc.).")
    winner_lawyers: list[LawyerInfo] = Field(default_factory=list, description="List of winning lawyers.")
    loser_lawyers: list[LawyerInfo] = Field(default_factory=list, description="List of losing lawyers.")


    class Config:
        json_schema_extra = {
            "example": {
                "intimation_id": 12345,
                "process_number": "0001-01.2024.8.22.0001",
                "tribunal": "TJRO",
                "decision_date": "2024-01-15",
                "download_url": "http://example.com/document.pdf",
                "needs_download": True,
                "ia_url": "https://archive.org/details/12345",
                "gemini_summary": "The court denied the appeal.",
                "full_decision_text": "Full text of the acordão...",
                "outcome": "LOSS",
                "winner_lawyers": [{"oab_number": "123", "oab_state": "RO", "name": "Winning Lawyer"}],
                "loser_lawyers": [{"oab_number": "456", "oab_state": "RO", "name": "Losing Lawyer"}],
            },
        }
