import unittest
from pathlib import Path
import tempfile
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from database import CausaGanhaDB
from queues.base import QueueProcessor, QueueItem


class DummyProcessor(QueueProcessor):
    def get_pending_items(self, limit: int = 10):
        items = []
        rows = self.db.get_pending_discovery_items(limit)
        for r in rows:
            items.append(
                QueueItem(
                    id=r["id"],
                    status=r["status"],
                    attempts=r["attempts"],
                    last_attempt=r["last_attempt"],
                    error_message=r["error_message"],
                    metadata=r["metadata"],
                )
            )
        return items

    def process_item(self, item: QueueItem) -> bool:
        return True

    def update_item_status(self, item_id: int, status: str, error: str | None = None):
        self.db.update_discovery_item_status(item_id, status, error)


class TestQueueProcessor(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.duckdb"
        self.db = CausaGanhaDB(self.db_path)
        self.db.connect()
        self.db.add_to_discovery_queue("http://example.com/a.pdf", "2024-01-01", year=2024)
        self.db.add_to_discovery_queue("http://example.com/b.pdf", "2024-01-02", year=2024)

    def tearDown(self):
        self.db.close()
        self.tmpdir.cleanup()

    def test_run_batch(self):
        processor = DummyProcessor(self.db)
        results = processor.run_batch(batch_size=2)
        self.assertEqual(results["processed"], 2)
        self.assertEqual(results["succeeded"], 2)
        self.assertEqual(results["failed"], 0)
        pending = self.db.get_pending_discovery_items(10)
        self.assertEqual(len(pending), 0)


if __name__ == "__main__":
    unittest.main()
