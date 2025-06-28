from datetime import date
import pytest
from pydantic import BaseModel, ValidationError, HttpUrl


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
