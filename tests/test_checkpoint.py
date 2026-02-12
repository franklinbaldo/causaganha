"""BDD step definitions for consolidation checkpoint logic."""

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Ensure the pipeline scripts directory is importable
# Path: causaganha/scripts/pipeline/consolidate.py
# Test file path: causaganha/tests/test_checkpoint.py
# scripts_dir is at ../scripts/pipeline/ relative to tests/
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "pipeline"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from consolidate import find_next_unconsolidated  # noqa: E402


FEATURE = "features/checkpoint.feature"


@scenario(FEATURE, "Consolidation saves checkpoint after checking dates")
def test_checkpoint_saves_after_checking():
    pass


@scenario(FEATURE, "Consolidation resumes from last checkpoint")
def test_checkpoint_resumes():
    pass


@pytest.fixture
def context():
    return {"checked_dates": []}


# ==============================================================================
# GIVEN STEPS
# ==============================================================================


@given("a clean environment with no backfill checkpoint")
def clean_environment(tmp_path, context):
    context["checkpoint_file"] = tmp_path / "backfill_checkpoint.json"
    if context["checkpoint_file"].exists():
        context["checkpoint_file"].unlink()


@given(parsers.parse("a checkpoint exists for {days:d} days ago"))
def existing_checkpoint(tmp_path, context, days):
    context["checkpoint_file"] = tmp_path / "backfill_checkpoint.json"
    # Find a weekday that's approximately 'days' days ago
    today = date.today()
    candidate = today - timedelta(days=days)
    # If it's a weekend, move to the previous Friday
    while candidate.weekday() >= 5:  # Saturday=5, Sunday=6
        candidate -= timedelta(days=1)
    last_date = candidate.strftime("%Y-%m-%d")
    context["initial_date"] = last_date
    context["initial_days_ago"] = (today - candidate).days
    with open(context["checkpoint_file"], "w") as f:
        json.dump({"last_checked": last_date}, f)


# ==============================================================================
# WHEN STEPS
# ==============================================================================


@when("I find the next unconsolidated date")
def scan_unconsolidated(context):
    checkpoint_file = context["checkpoint_file"]
    checked_dates = []

    def mock_needs(d_str, *args, **kwargs):
        checked_dates.append(d_str)
        return False  # Continue scanning

    # Limit scan to 10 days to avoid long tests
    def stopped_side_effect(d, *args, **kwargs):
        return (date.today() - d).days > 10

    with (
        patch("consolidate._all_tribunals_stopped", side_effect=stopped_side_effect),
        patch("consolidate._needs_consolidation", side_effect=mock_needs),
        patch("consolidate.fetch_consolidation_candidates", return_value=[]),
    ):
        find_next_unconsolidated(checkpoint_file=checkpoint_file)

    context["checked_dates"] = checked_dates


# ==============================================================================
# THEN STEPS
# ==============================================================================


@then("the checkpoint file should be created")
def checkpoint_file_exists(context):
    assert context["checkpoint_file"].exists()


@then("the checkpoint should contain the last date checked")
def checkpoint_contains_date(context):
    with open(context["checkpoint_file"]) as f:
        data = json.load(f)

    assert "last_checked" in data
    # The last checked date should be the one where the scan stopped (11 days ago)
    last_checked = (date.today() - timedelta(days=11)).strftime("%Y-%m-%d")
    # Actually it depends on how find_next_unconsolidated handles the stop condition.
    # In the code:
    # if _all_tribunals_stopped(d): return None
    # otherwise it checks and saves.
    # So if it stops at 11 days ago, the last SAVED one was 10 days ago (or 11 if it saved before returning None)
    # Looking at the code:
    # if _all_tribunals_stopped(d): return None
    # if _needs_consolidation(d_str, ...):
    #    checkpoint.save(d_str)
    #    return d_str
    # checkpoint.save(d_str)
    # days_ago += 1

    # It saves EVERY date it checks.
    assert data["last_checked"] in context["checked_dates"]


@then(parsers.parse("it should skip checking dates from the last {days:d} days"))
def check_skipped_dates(context, days):
    today = date.today()
    # The actual days skipped depends on the checkpoint date
    # (which may have been adjusted to avoid weekends)
    initial_days_ago = context.get("initial_days_ago", days)
    skipped = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(initial_days_ago)]
    for d in skipped:
        assert d not in context["checked_dates"]


@then(parsers.parse("resume scanning from {days:d} days ago"))
def check_resume_date(context, days):
    # Use the actual date from the checkpoint (which may have been adjusted for weekends)
    resume_date = context.get("initial_date")
    if resume_date is None:
        resume_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    assert resume_date in context["checked_dates"]
    # It should be the first date checked
    assert context["checked_dates"][0] == resume_date
