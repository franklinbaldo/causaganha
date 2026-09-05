#!/usr/bin/env python3
"""CI/loop check: report which `AgentRun` fields a round report still owes.

Purpose:  Tell the hourly Claude Code loop exactly which `AgentRun` fields its
          round report (`knowledge/agent-runs/<run-id>/run.md`) still needs to
          fill in before the round can close.
Problem:  `knowledge/okf.schema.sql` declares `NOT NULL`/`CHECK` constraints on
          `AgentRun` (PR #1141) meant to make an incomplete scaffold invalid.
          okf-parser 0.45.6 does not enforce them: `check --relational-schema`
          only reads PRIMARY KEY/FOREIGN KEY catalog metadata, and
          `compile_types` rebuilds each declared table from bare column types,
          dropping every constraint. So the shipped scaffold — every field
          present as `""`/`[]` — validates as conformant today.
Strategy: Re-implement the same "required, non-empty" contract in Python,
          mirroring `knowledge/okf.schema.sql`'s `AgentRun` constraints field
          for field, and read frontmatter with the real okf-parser contract
          (`okf_parser.parser.parse_document`).
Status:   used by `.claude/hourly-loop.md`'s validation loop; see
          `knowledge/agent-runs/README.md`.

Usage:
    uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/<run-id>/run.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from okf_parser.models import YamlValue

REQUIRED_TEXT_FIELDS = (
    "id",
    "started_at",
    "completed_at",
    "branch_at_start",
    "commit_at_start",
    "claude_md_reading_id",
    "issues_reading_id",
    "prs_reading_id",
    "okf_reading_id",
    "primary_goal_id",
    "selected_work",
    "expected_behavior",
    "result_summary",
    "next_move",
)

REQUIRED_LIST_FIELDS = (
    "goal_ids",
    "considered_work",
    "decision_ids",
    "evidence_ids",
    "check_ids",
)

ENUM_FIELDS: dict[str, frozenset[str]] = {
    "entry_state": frozenset({"new", "red", "green", "review", "blocked"}),
    "target_state": frozenset({"red", "green", "review", "merged", "unblocked"}),
    "result_state": frozenset({"red", "green", "review", "merged", "blocked"}),
}


def missing_agent_run_fields(frontmatter: dict[str, YamlValue]) -> list[str]:
    """Names of `AgentRun` fields that still violate the round-close contract.

    Mirrors `knowledge/okf.schema.sql`'s `AgentRun` table field for field:
    a required text field must be a non-blank string, a required list field
    must hold at least one entry, and an enum field must hold one of its
    declared values.
    """
    missing: list[str] = []
    for field in REQUIRED_TEXT_FIELDS:
        value = frontmatter.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    for field in REQUIRED_LIST_FIELDS:
        value = frontmatter.get(field)
        if not isinstance(value, list) or not value:
            missing.append(field)
    for field, allowed in ENUM_FIELDS.items():
        value = frontmatter.get(field)
        if value not in allowed:
            missing.append(field)
    return sorted(missing)


def main(argv: list[str] | None = None) -> int:
    from okf_parser.parser import parse_document

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Path to an AgentRun run.md document.")
    args = parser.parse_args(argv)

    frontmatter = parse_document(args.path).frontmatter
    concept_type = frontmatter.get("type")
    if concept_type != "AgentRun":
        print(f"❌ {args.path} has type {concept_type!r}, expected 'AgentRun'.")
        return 1

    missing = missing_agent_run_fields(frontmatter)
    if not missing:
        print(f"✅ {args.path} — AgentRun round report is complete.")
        return 0

    print(f"❌ {args.path} — AgentRun round report is still missing:")
    for field in missing:
        print(f"  - {field}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
