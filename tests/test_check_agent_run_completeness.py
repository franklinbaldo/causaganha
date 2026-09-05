"""`AgentRun` completeness is not actually enforced by `okf-parser check`.

`knowledge/okf.schema.sql` declares `NOT NULL`/`CHECK` constraints on `AgentRun`
(PR #1141) so an hourly-loop round's report is meant to "grow into" a valid,
complete document. But okf-parser 0.45.6's `--relational-schema` only reads
`PRIMARY KEY`/`FOREIGN KEY` metadata from the DuckDB catalog
(`relational_schema.py`'s `parse_relational_schema`) and `compile_types`
rebuilds each declared table from bare column types only (`DeclaredSchema`
keeps `columns: dict[str, DuckDBLogicalType]`, nothing else) — so `CHECK`
constraints are decorative today: an all-empty `AgentRun` scaffold reports
`conformant: true`. `scripts/check_agent_run_completeness.py` closes that gap
in the project's own tooling, independent of upstream okf-parser support.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_agent_run_completeness import missing_agent_run_fields


REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD = REPO_ROOT / ".claude" / "agent-run-scaffold.md"

_COMPLETE_FRONTMATTER = {
    "type": "AgentRun",
    "id": "2026-09-05-example",
    "started_at": "2026-09-05T00:00:00Z",
    "completed_at": "2026-09-05T01:00:00Z",
    "branch_at_start": "main",
    "commit_at_start": "abc123",
    "claude_md_reading_id": "reading-claude-md",
    "issues_reading_id": "reading-issues",
    "prs_reading_id": "reading-prs",
    "okf_reading_id": "reading-okf",
    "goal_ids": ["goal-1"],
    "primary_goal_id": "goal-1",
    "considered_work": ["option a", "option b"],
    "selected_work": "option a",
    "expected_behavior": "the thing behaves like this",
    "entry_state": "new",
    "target_state": "green",
    "decision_ids": ["decision-1"],
    "evidence_ids": ["evidence-1"],
    "check_ids": ["check-1"],
    "result_state": "green",
    "result_summary": "did the thing",
    "next_move": "do the next thing",
}


def test_scaffold_is_reported_conformant_by_okf_parser_alone() -> None:
    """Documents the gap: the shipped scaffold is intentionally incomplete,
    but has no way to say so through `okf-parser check --relational-schema`
    alone — every field is present as an empty string/list, which satisfies
    the catalog-level PK/FK checks that command actually runs."""
    from okf_parser.parser import parse_document

    frontmatter = parse_document(SCAFFOLD).frontmatter
    assert frontmatter["id"] == ""
    assert missing_agent_run_fields(frontmatter) != []


def test_all_empty_scaffold_reports_every_required_field_missing() -> None:
    frontmatter = {
        key: "" if not isinstance(value, list) else []
        for key, value in _COMPLETE_FRONTMATTER.items()
    }
    missing = missing_agent_run_fields(frontmatter)
    assert "id" in missing
    assert "goal_ids" in missing
    assert "result_summary" in missing
    assert len(missing) >= 20


def test_fully_filled_run_has_no_missing_fields() -> None:
    assert missing_agent_run_fields(_COMPLETE_FRONTMATTER) == []


def test_invalid_enum_value_is_reported_missing() -> None:
    frontmatter = dict(_COMPLETE_FRONTMATTER, result_state="not-a-real-state")
    assert "result_state" in missing_agent_run_fields(frontmatter)


def test_absent_key_is_reported_missing() -> None:
    frontmatter = dict(_COMPLETE_FRONTMATTER)
    del frontmatter["next_move"]
    assert "next_move" in missing_agent_run_fields(frontmatter)


@pytest.mark.parametrize(
    "field", ["goal_ids", "decision_ids", "evidence_ids", "check_ids", "considered_work"]
)
def test_empty_list_field_is_reported_missing(field: str) -> None:
    frontmatter = dict(_COMPLETE_FRONTMATTER, **{field: []})
    assert field in missing_agent_run_fields(frontmatter)
