"""Module-surface regression guard for SyncConfig/PipelineRunConfig.

``skip_if_mostly_complete`` and ``publish_live_status`` were set on
``SyncConfig``/``PipelineRunConfig`` at every construction site but never
read anywhere afterward -- and no CLI flag ever set them to anything but
their hardcoded ``False`` default, so there was no live contract to honor.
Removed rather than repaired, per this repository's established dead-code
pattern: a never-read field delivers no product value to keep (see
tests/consolidate/test_candidates_module_surface.py for the precedent).
"""

from __future__ import annotations

import dataclasses

from djen_backup.engine import SyncConfig
from djen_backup.service import PipelineRunConfig


def test_dead_flags_removed_from_sync_config() -> None:
    field_names = {f.name for f in dataclasses.fields(SyncConfig)}
    assert "skip_if_mostly_complete" not in field_names
    assert "publish_live_status" not in field_names


def test_dead_flags_removed_from_pipeline_run_config() -> None:
    field_names = {f.name for f in dataclasses.fields(PipelineRunConfig)}
    assert "skip_if_mostly_complete" not in field_names
    assert "publish_live_status" not in field_names
