from datetime import date
from pathlib import Path

from models.diario import Diario


def test_to_dict_and_from_dict_roundtrip():
    original = Diario(
        tribunal="tjro",
        data=date(2025, 6, 26),
        url="https://example.com/diario.pdf",
        filename="diario.pdf",
        pdf_path=Path("/tmp/diario.pdf"),
        metadata={"k": "v"},
    )
    data_dict = original.to_dict()
    restored = Diario.from_dict(data_dict)
    assert restored.tribunal == original.tribunal
    assert restored.data == original.data
    assert restored.url == original.url
    assert restored.filename == original.filename
    assert restored.pdf_path == original.pdf_path
    assert restored.metadata == original.metadata


def test_from_dict_missing_optional_fields():
    restored = Diario.from_dict(
        {"tribunal": "tjro", "data": "2025-06-26", "url": "u"}
    )
    assert restored.filename is None
    assert restored.pdf_path is None
    assert restored.metadata == {}
