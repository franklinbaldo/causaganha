import pytest
from datetime import date
from unittest.mock import patch

from tribunais import register_tribunal, get_adapter, list_supported_tribunals
from models.diario import Diario
from models.interfaces import (
    DiarioDiscovery,
    DiarioDownloader,
    DiarioAnalyzer,
    TribunalAdapter,
)


def make_dummy_classes(code: str):
    class DummyDiscovery(DiarioDiscovery):
        def __init__(self):
            self._code = code

        def get_diario_url(self, target_date: date):
            return f"https://example.com/{code}/{target_date.isoformat()}.pdf"

        def get_latest_diario_url(self):
            return self.get_diario_url(date.today())

        @property
        def tribunal_code(self) -> str:
            return self._code

    class DummyDownloader(DiarioDownloader):
        def download_diario(self, diario: Diario) -> Diario:  # pragma: no cover - simple stub
            diario.pdf_path = None
            diario.update_status("downloaded")
            return diario

        def archive_to_ia(self, diario: Diario) -> Diario:  # pragma: no cover - simple stub
            diario.ia_identifier = f"ia-{code}"
            return diario

    class DummyAnalyzer(DiarioAnalyzer):
        def extract_decisions(self, diario: Diario):  # pragma: no cover - simple stub
            return []

    class DummyAdapter(TribunalAdapter):
        @property
        def discovery(self) -> DummyDiscovery:
            return DummyDiscovery()

        @property
        def downloader(self) -> DummyDownloader:
            return DummyDownloader()

        @property
        def analyzer(self) -> DummyAnalyzer:
            return DummyAnalyzer()

        @property
        def tribunal_code(self) -> str:
            return code

    return DummyDiscovery, DummyDownloader, DummyAnalyzer, DummyAdapter


@pytest.mark.parametrize("code", ["tja", "tjb"])
def test_register_and_get_adapter(code):
    discovery, downloader, analyzer, adapter = make_dummy_classes(code)
    register_tribunal(code, discovery, downloader, analyzer, adapter)

    assert code in list_supported_tribunals()

    adapter_instance = get_adapter(code)
    assert adapter_instance.tribunal_code == code

    diario = adapter_instance.create_diario(date(2025, 1, 1))
    assert isinstance(diario, Diario)
    assert diario.tribunal == code

@pytest.mark.parametrize("tribunal", list_supported_tribunals())
def test_real_adapters_create_diario(tribunal):
    adapter = get_adapter(tribunal)
    with patch.object(adapter.discovery, "get_diario_url", return_value="https://example.com/test.pdf"):
        diario = adapter.create_diario(date(2025, 1, 2))
    assert isinstance(diario, Diario)
    assert diario.tribunal == tribunal
