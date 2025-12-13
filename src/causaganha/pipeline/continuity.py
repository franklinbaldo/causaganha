from datetime import datetime

from ibis import BaseBackend

from causaganha.storage.connection import get_connection
from causaganha.storage.schema import create_schema


class ContinuityManager:
    """Manages the continuity of the pipeline processing, allowing tasks to be resumed."""

    def __init__(self, con: BaseBackend | None = None):
        """Initialize the ContinuityManager.

        Args:
            con: Ibis DuckDB connection backend. If None, creates a new connection using default config.
        """
        if con is None:
            self.con = get_connection()
            create_schema(self.con)
        else:
            self.con = con

    def is_done(self, task_id: str, step: str) -> bool:
        """Check if a task step has been completed.

        Args:
            task_id: Unique identifier for the task (e.g., process number).
            step: The step name (e.g., 'collection', 'analysis').

        Returns:
            True if the step is marked as done, False otherwise.
        """
        t = self.con.table("pipeline_state")
        count = t.filter((t.task_id == task_id) & (t.step == step)).count().execute()
        return int(count) > 0

    def mark_done(self, task_id: str, step: str) -> None:
        """Mark a task step as completed.

        Args:
            task_id: Unique identifier for the task.
            step: The step name.
        """
        if not self.is_done(task_id, step):
            # Using raw SQL for DuckDB simple insert
            query = "INSERT INTO pipeline_state (task_id, step, timestamp) VALUES (?, ?, ?)"
            self.con.con.execute(query, [task_id, step, datetime.now()])
