"""Structural invariants for the cross-round 'blocked backlog' cache.

Problem: at least ~10 consecutive hourly-loop rounds independently re-read and
re-justified the same set of blocked/deprioritized GitHub issues, because
every `AgentReading` is scoped to a single round's `run_id` and lives inside
that round's own `knowledge/agent-runs/<run-id>/` directory — the fact dies
with the round. `knowledge/backlog/` holds one `BacklogItem` per currently
open issue instead, outside any single round's directory, so a future round
can read *why* an issue is still blocked and *when* that was last verified
instead of re-deriving it from the GitHub issue tracker every time.

This test enforces the structural contract `knowledge/okf.schema.sql`
declares for `BacklogItem` (unique `issue_number`, valid `category`/`status`,
non-blank reasoning fields, and a `last_verified_run_id` that actually
resolves to a real completed round) — the same role
`tests/test_check_agent_run_completeness.py` plays for the `AgentRun` family,
since `okf-parser check --relational-schema` only validates PK/FK catalog
metadata, not `CHECK` constraints or cross-file existence.
"""

from __future__ import annotations

from pathlib import Path

from okf_parser.parser import parse_document


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKLOG_DIR = REPO_ROOT / "knowledge" / "backlog"
AGENT_RUNS_DIR = REPO_ROOT / "knowledge" / "agent-runs"

VALID_CATEGORIES = {
    "ml_data_work",
    "credentials",
    "infra_decision",
    "deprioritized_by_owner",
}
VALID_STATUSES = {"blocked", "deprioritized", "unblocked"}
REQUIRED_TEXT_FIELDS = (
    "title",
    "blocking_reason",
    "unblock_condition",
    "last_verified_at",
    "last_verified_run_id",
)


def _backlog_items() -> list[tuple[Path, dict]]:
    files = sorted(BACKLOG_DIR.glob("issue-*.md")) if BACKLOG_DIR.is_dir() else []
    return [(f, parse_document(f).frontmatter) for f in files]


def test_backlog_directory_exists_and_is_nonempty() -> None:
    assert BACKLOG_DIR.is_dir(), "knowledge/backlog/ must exist"
    assert _backlog_items(), "knowledge/backlog/ must contain at least one BacklogItem"


def test_every_backlog_item_declares_type_backlog_item() -> None:
    for path, frontmatter in _backlog_items():
        assert frontmatter.get("type") == "BacklogItem", f"{path}: type must be BacklogItem"


def test_every_backlog_item_has_unique_issue_number() -> None:
    # okf_parser's raw frontmatter parse keeps scalars as strings (schema-driven
    # int coercion only happens in compile_types), so accept str or int here and
    # just require each to represent a positive integer.
    raw_numbers = [frontmatter.get("issue_number") for _, frontmatter in _backlog_items()]
    numbers = [int(n) for n in raw_numbers]
    assert all(n > 0 for n in numbers), f"issue_number must be a positive integer: {raw_numbers}"
    assert len(numbers) == len(set(numbers)), (
        f"duplicate issue_number in knowledge/backlog/: {raw_numbers}"
    )


def test_every_backlog_item_declares_valid_category_and_status() -> None:
    for path, frontmatter in _backlog_items():
        category = frontmatter.get("category")
        status = frontmatter.get("status")
        assert category in VALID_CATEGORIES, f"{path}: invalid category {category!r}"
        assert status in VALID_STATUSES, f"{path}: invalid status {status!r}"


def test_every_backlog_item_has_nonblank_reasoning_fields() -> None:
    for path, frontmatter in _backlog_items():
        for field in REQUIRED_TEXT_FIELDS:
            value = frontmatter.get(field)
            assert isinstance(value, str) and value.strip(), (
                f"{path}: {field} must be a non-blank string"
            )


def test_every_backlog_item_last_verified_run_id_resolves_to_a_real_agent_run() -> None:
    for path, frontmatter in _backlog_items():
        run_id = frontmatter["last_verified_run_id"]
        run_file = AGENT_RUNS_DIR / run_id / "run.md"
        assert run_file.is_file(), (
            f"{path}: last_verified_run_id {run_id!r} has no knowledge/agent-runs/{run_id}/run.md"
        )
