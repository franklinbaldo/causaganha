from __future__ import annotations

import json
import requests
from datetime import datetime
from typing import List

from .base import QueueItem, QueueProcessor


class PDFDiscoveryProcessor(QueueProcessor):
    """Processor for discovering new PDF URLs."""

    discovery_url = "https://www.tjro.jus.br/diario_oficial/data-ultimo-diario.php"

    def get_pending_items(self, limit: int = 10) -> List[QueueItem]:
        rows = self.db.conn.execute(
            """
            SELECT id, status, attempts, last_attempt, error_message, metadata
            FROM pdf_discovery_queue
            WHERE status = 'pending'
            ORDER BY priority DESC, id
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        items: List[QueueItem] = []
        for r in rows:
            meta = json.loads(r[5]) if r[5] else {}
            items.append(
                QueueItem(
                    id=r[0],
                    status=r[1],
                    attempts=r[2],
                    last_attempt=r[3],
                    error_message=r[4],
                    metadata=meta,
                )
            )
        return items

    def update_item_status(self, item_id: int, status: str, error: str | None = None) -> None:
        self.db.conn.execute(
            """
            UPDATE pdf_discovery_queue
            SET status = ?, attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP, error_message = ?
            WHERE id = ?
            """,
            [status, error, item_id],
        )

    def process_item(self, item: QueueItem) -> bool:
        """Download PDF metadata and enqueue download."""
        try:
            pdf_url = item.metadata.get("url")
            if not pdf_url:
                raise ValueError("Missing PDF URL")
            # Validate URL by making a HEAD request
            resp = requests.head(pdf_url, timeout=10)
            resp.raise_for_status()
            self.db.conn.execute(
                "INSERT INTO pdf_archive_queue (pdf_id, local_path) VALUES (?, ?)",
                [item.metadata.get("pdf_id", 0), pdf_url],
            )
            return True
        except Exception as exc:
            self.logger.error("Discovery failed for %s: %s", pdf_url, exc)
            return False
