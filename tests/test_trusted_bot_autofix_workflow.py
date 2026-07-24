# Copyright (c) 2026 CausaGanha Team
"""Contract tests for the write-capable trusted-bot workflow guard."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/trusted-bot-autofix.yml"
FIXTURES = ROOT / ".github/workflows/fixtures/trusted-bot-autofix-events.json"
EXPECTED_CONDITION = (
    "github.event.pull_request.head.repo.full_name == github.repository && "
    "github.event.pull_request.user.login == 'dependabot[bot]' && "
    "github.actor == 'dependabot[bot]'"
)


def auto_fix_is_allowed(event: dict[str, object]) -> bool:
    """Mirror the documented GitHub Actions condition for fixture coverage."""
    return (
        event["head_repository"] == event["repository"]
        and event["pull_request_author"] == "dependabot[bot]"
        and event["actor"] == "dependabot[bot]"
    )


def test_trusted_bot_auto_fix_guard_matches_event_fixture() -> None:
    events = json.loads(FIXTURES.read_text())

    assert [auto_fix_is_allowed(event) for event in events] == [
        event["allowed"] for event in events
    ]


def test_write_workflow_uses_the_explicit_trusted_bot_guard() -> None:
    workflow = WORKFLOW.read_text()

    assert "pull_request_target:" in workflow
    assert "permissions:\n  contents: write" in workflow
    assert EXPECTED_CONDITION in " ".join(workflow.split())
    assert "persist-credentials: false" in workflow
