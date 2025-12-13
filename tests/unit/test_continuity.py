from datetime import datetime
import pytest
from ibis import BaseBackend

from causaganha.pipeline.continuity import ContinuityManager
from causaganha.storage.connection import get_connection


@pytest.fixture
def db_connection() -> BaseBackend:
    """Fixture to provide an in-memory database connection."""
    return get_connection(":memory:")


@pytest.fixture
def continuity_manager(db_connection: BaseBackend) -> ContinuityManager:
    """Fixture to provide a ContinuityManager instance."""
    return ContinuityManager(con=db_connection)


def test_is_done_initially_false(continuity_manager: ContinuityManager) -> None:
    """Test that is_done returns False for a new task."""
    assert continuity_manager.is_done("task_123", "collection") is False


def test_mark_done(
    continuity_manager: ContinuityManager, db_connection: BaseBackend
) -> None:
    """Test that mark_done correctly records the task completion."""
    task_id = "task_123"
    step = "collection"

    continuity_manager.mark_done(task_id, step)

    # Verify via manager
    assert continuity_manager.is_done(task_id, step) is True

    # Verify via direct DB query
    t = db_connection.table("pipeline_state")
    rows = t.filter((t.task_id == task_id) & (t.step == step)).execute()
    assert len(rows) == 1
    assert rows.iloc[0]["task_id"] == task_id
    assert rows.iloc[0]["step"] == step
    assert isinstance(rows.iloc[0]["timestamp"], datetime)


def test_is_done_specific(continuity_manager: ContinuityManager) -> None:
    """Test that is_done is specific to task_id and step."""
    continuity_manager.mark_done("task_A", "step_1")

    assert continuity_manager.is_done("task_A", "step_1") is True
    assert continuity_manager.is_done("task_A", "step_2") is False
    assert continuity_manager.is_done("task_B", "step_1") is False


def test_mark_done_idempotent(
    continuity_manager: ContinuityManager, db_connection: BaseBackend
) -> None:
    """Test that mark_done can be called multiple times without error."""
    task_id = "task_idem"
    step = "test"

    continuity_manager.mark_done(task_id, step)

    # Check timestamp logic later if needed, but unused variable removed.

    # Wait a tiny bit or just call again
    continuity_manager.mark_done(task_id, step)

    t = db_connection.table("pipeline_state")
    rows = t.filter((t.task_id == task_id) & (t.step == step)).execute()

    # Assert that we have at least one record.
    assert len(rows) >= 1
    assert continuity_manager.is_done(task_id, step) is True
