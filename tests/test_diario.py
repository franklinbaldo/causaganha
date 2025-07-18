"""
Tests for the Diario dataclass implementation.
"""

import unittest
from datetime import date
from pathlib import Path
import json
import sys

from models.diario import Diario  # Moved to top
from tribunais import (
    get_adapter,
    is_tribunal_supported,
    list_supported_tribunals,
)  # Moved to top
# Specific import for testing can remain if not causing E402, or also moved.
# from tribunais.tjro.adapter import TJROAdapter

# Add src directory to path for testing
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


class TestDiario(unittest.TestCase):
    """Test the Diario dataclass."""

    def test_diario_creation(self):
        """Test creating a basic Diario object."""
        diario = Diario(
            tribunal="tjro",
            data=date(2025, 6, 26),
            url="https://tjro.jus.br/test.pdf",
            filename="test.pdf",
        )

        self.assertEqual(diario.tribunal, "tjro")
        self.assertEqual(diario.data, date(2025, 6, 26))
        self.assertEqual(diario.url, "https://tjro.jus.br/test.pdf")
        self.assertEqual(diario.filename, "test.pdf")
        self.assertEqual(diario.status, "pending")
        self.assertEqual(diario.display_name, "TJRO - 2025-06-26")

    def test_queue_item_conversion(self):
        """Test converting Diario to queue item format."""
        diario = Diario(
            tribunal="tjro",
            data=date(2025, 6, 26),
            url="https://tjro.jus.br/test.pdf",
            filename="test.pdf",
            status="downloaded",
            metadata={"test": "value"},
        )

        queue_item = diario.queue_item

        self.assertEqual(queue_item["url"], "https://tjro.jus.br/test.pdf")
        self.assertEqual(queue_item["date"], "2025-06-26")
        self.assertEqual(queue_item["tribunal"], "tjro")
        self.assertEqual(queue_item["filename"], "test.pdf")
        self.assertEqual(queue_item["status"], "downloaded")
        self.assertEqual(queue_item["metadata"], {"test": "value"})

    def test_from_queue_item(self):
        """Test creating Diario from queue item data."""
        queue_data = {
            "url": "https://tjro.jus.br/test.pdf",
            "date": "2025-06-26",
            "tribunal": "tjro",
            "filename": "test.pdf",
            "status": "analyzed",
            "metadata": json.dumps(
                {"test": "value"}
            ),  # metadata in DB is TEXT (json string)
            "ia_identifier": "test-identifier",
            "arquivo_path": "/path/to/file.pdf",
        }

        diario = Diario.from_queue_item(queue_data)

        self.assertEqual(diario.tribunal, "tjro")
        self.assertEqual(diario.data, date(2025, 6, 26))
        self.assertEqual(diario.url, "https://tjro.jus.br/test.pdf")
        self.assertEqual(diario.filename, "test.pdf")
        self.assertEqual(diario.status, "analyzed")
        self.assertEqual(
            diario.metadata, {"test": "value"}
        )  # from_queue_item should parse JSON string
        self.assertEqual(diario.ia_identifier, "test-identifier")
        self.assertEqual(str(diario.pdf_path), "/path/to/file.pdf")

    def test_update_status(self):
        """Test updating diario status and metadata."""
        diario = Diario(
            tribunal="tjro", data=date(2025, 6, 26), url="https://tjro.jus.br/test.pdf"
        )

        diario.update_status("downloaded", pdf_path=Path("/test/path.pdf"))

        self.assertEqual(diario.status, "downloaded")
        self.assertEqual(diario.pdf_path, Path("/test/path.pdf"))

    def test_dict_conversion(self):
        """Test converting to/from dictionary."""
        original = Diario(
            tribunal="tjro",
            data=date(2025, 6, 26),
            url="https://tjro.jus.br/test.pdf",
            filename="test.pdf",
            pdf_path=Path("/test/path.pdf"),
            metadata={"test": "value"},
        )

        dict_data = original.to_dict()
        restored = Diario.from_dict(dict_data)

        self.assertEqual(original.tribunal, restored.tribunal)
        self.assertEqual(original.data, restored.data)
        self.assertEqual(original.url, restored.url)
        self.assertEqual(original.filename, restored.filename)
        self.assertEqual(original.pdf_path, restored.pdf_path)
        self.assertEqual(original.metadata, restored.metadata)


class TestTribunalRegistry(unittest.TestCase):
    """Test the tribunal registry system."""

    def test_supported_tribunals(self):
        """Test tribunal support checking."""
        supported = list_supported_tribunals()

        self.assertIn("tjro", supported)
        self.assertTrue(is_tribunal_supported("tjro"))
        self.assertFalse(is_tribunal_supported("nonexistent"))

    def test_get_adapter(self):
        """Test getting tribunal adapter."""
        adapter = get_adapter("tjro")
        from tribunais.tjro.adapter import TJROAdapter  # Import here to check type

        self.assertIsInstance(adapter, TJROAdapter)
        self.assertEqual(adapter.tribunal_code, "tjro")
        self.assertIsNotNone(adapter.discovery)
        self.assertIsNotNone(adapter.downloader)
        self.assertIsNotNone(adapter.analyzer)

    def test_unsupported_tribunal(self):
        """Test error handling for unsupported tribunal."""
        with self.assertRaises(ValueError):
            get_adapter("nonexistent")


class TestTJROIntegration(unittest.TestCase):
    """Test TJRO-specific implementations."""

    def test_tjro_discovery_properties(self):
        """Test TJRO discovery basic properties."""
        from tribunais.tjro.discovery import TJRODiscovery

        discovery = TJRODiscovery()
        self.assertEqual(discovery.tribunal_code, "tjro")
        self.assertEqual(
            discovery.TJRO_BASE_URL, "https://www.tjro.jus.br/diario_oficial/"
        )

    def test_tjro_adapter_creation(self):
        """Test creating TJRO adapter."""
        adapter = get_adapter("tjro")
        from tribunais.tjro.adapter import TJROAdapter

        self.assertIsInstance(adapter, TJROAdapter)

        self.assertEqual(adapter.tribunal_code, "tjro")
        self.assertTrue(hasattr(adapter, "create_diario"))
        self.assertTrue(hasattr(adapter, "process_diario"))

    def test_update_status_extra_field(self):
        """Unknown kwargs should be stored in metadata."""
        diario = Diario(tribunal="tjro", data=date(2025, 6, 27), url="u")
        diario.update_status("downloaded", custom="yes")
        self.assertEqual(diario.status, "downloaded")
        self.assertEqual(diario.metadata.get("custom"), "yes")

    def test_from_queue_item_bad_json(self):
        """Invalid JSON metadata should result in empty dict."""
        queue_data = {
            "url": "https://tjro.jus.br/test.pdf",
            "date": "2025-06-26",
            "tribunal": "tjro",
            "metadata": "not-json",
        }
        diario = Diario.from_queue_item(queue_data)
        self.assertEqual(diario.metadata, {})


if __name__ == "__main__":
    unittest.main()
