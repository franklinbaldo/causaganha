from datetime import date
import pytest
from pydantic import BaseModel, ValidationError, HttpUrl
from datetime import datetime
from models.llm_output import Decision, ExtractionResult


class DiarioModel(BaseModel):
    tribunal: str
    data: date
    url: HttpUrl
    filename: str | None = None


def test_diario_model_accepts_valid_data():
    model = DiarioModel(
        tribunal="tjro",
        data=date(2025, 6, 26),
        url="https://example.com/diario.pdf",
        filename="diario.pdf",
    )
    assert model.tribunal == "tjro"
    assert model.filename == "diario.pdf"


def test_diario_model_rejects_invalid_url():
    with pytest.raises(ValidationError):
        DiarioModel(
            tribunal="tjro",
            data=date(2025, 6, 26),
            url="not-a-url",
        )


def test_decision_model_valid():
    decision = Decision(
        numero_processo="123",
        resultado="procedente",
        data_decisao=date(2025, 6, 26),
    )
    assert decision.numero_processo == "123"


def test_decision_model_missing_field():
    with pytest.raises(ValidationError):
        Decision(resultado="ok", data_decisao=date(2025, 6, 26))


def test_extraction_result_valid():
    decision = Decision(
        numero_processo="123",
        resultado="ok",
        data_decisao=date(2025, 6, 26),
    )
    model = ExtractionResult(
        file_name_source="file.pdf",
        extraction_timestamp=datetime(2025, 6, 26, 12, 0, 0),
        decisions=[decision],
        chunks_processed=1,
        total_decisions_found=1,
    )
    assert model.total_decisions_found == 1


def test_extraction_result_invalid_decisions():
    with pytest.raises(ValidationError):
        ExtractionResult(
            file_name_source="file.pdf",
            extraction_timestamp=datetime(2025, 6, 26, 12, 0, 0),
            decisions="not-a-list",
            chunks_processed=0,
            total_decisions_found=0,
        )

