from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class QueueItem:
    """Representation of a generic queue item."""

    id: int
    status: str
    attempts: int
    last_attempt: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]


class QueueProcessor(ABC):
    """Abstract base class for queue processors."""

    def __init__(self, db: "CausaGanhaDB", max_attempts: int = 3) -> None:
        self.db = db
        self.max_attempts = max_attempts
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def get_pending_items(self, limit: int = 10) -> List[QueueItem]:
        """Fetch pending items from the queue."""

    @abstractmethod
    def process_item(self, item: QueueItem) -> bool:
        """Process a single queue item and return True on success."""

    @abstractmethod
    def update_item_status(self, item_id: int, status: str, error: str | None = None) -> None:
        """Persist item status to the database."""

    def _handle_failure(self, item: QueueItem, error: str | None = None) -> None:
        if item.attempts + 1 >= self.max_attempts:
            self.update_item_status(item.id, "failed", error)
            self.logger.error("Item %s failed permanently", item.id)
        else:
            self.update_item_status(item.id, "pending", error)
            self.logger.warning("Item %s failed, will retry", item.id)

    def run_batch(self, batch_size: int = 10) -> Dict[str, int]:
        """Process a batch of queue items."""
        items = self.get_pending_items(batch_size)
        results = {"processed": 0, "succeeded": 0, "failed": 0}

        for item in items:
            results["processed"] += 1
            try:
                self.update_item_status(item.id, "processing")
                success = self.process_item(item)
                if success:
                    self.update_item_status(item.id, "completed")
                    results["succeeded"] += 1
                else:
                    self._handle_failure(item)
                    results["failed"] += 1
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.error("Error processing item %s: %s", item.id, exc)
                self._handle_failure(item, str(exc))
                results["failed"] += 1
        return results
