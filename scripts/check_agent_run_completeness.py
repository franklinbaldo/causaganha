#!/usr/bin/env python3
"""CI/loop check: report which `Agent*` round-report fields a document still owes.

Purpose:  Tell the hourly Claude Code loop exactly which fields a round report
          document (`knowledge/agent-runs/<run-id>/**/*.md`) still needs to
          fill in before the round can close.
Problem:  `knowledge/okf.schema.sql` declares `NOT NULL`/`CHECK` constraints on
          `AgentRun` and its five sibling types — `AgentReading`, `AgentGoal`,
          `AgentDecision`, `AgentEvidence`, `AgentCheck` (PR #1141) — meant to
          make an incomplete scaffold invalid. okf-parser 0.45.6 does not
          enforce them: `check --relational-schema` only reads PRIMARY
          KEY/FOREIGN KEY catalog metadata, and `compile_types` rebuilds each
          declared table from bare column types, dropping every constraint.
          So a shipped scaffold — every field present as `""`/`[]` — validates
          as conformant today.
Strategy: Re-implement the same "required, non-empty" contract in Python,
          mirroring each table in `knowledge/okf.schema.sql` field for field,
          and read frontmatter with the real okf-parser contract
          (`okf_parser.parser.parse_document`). A single file is checked
          against its own declared `type`; a directory is scanned recursively
          and every recognized `Agent*` document under it is checked. Every
          frontmatter key is also checked against the exact columns
          `knowledge/okf.schema.sql` declares for that type
          (`unknown_fields_for_type`): a renamed or invented field (`title`
          where the schema says `goal`) is invisible to `okf-parser check`
          (PK/FK metadata only) and previously surfaced only much later, as an
          unrelated generated-file diff in `pytest -q`.
Status:   used by `.claude/hourly-loop.md`'s validation loop and by
          `.github/workflows/okf.yml`; see `knowledge/agent-runs/index.md`.

Usage:
    uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs/<run-id>/run.md
    uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from okf_parser.models import YamlValue

REQUIRED_TEXT_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "AgentRun": (
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
    ),
    "AgentReading": ("id", "run_id", "reference", "finding"),
    "AgentGoal": ("id", "run_id", "goal", "rationale", "success_signal"),
    "AgentDecision": ("id", "run_id", "question", "choice", "rationale"),
    "AgentEvidence": ("id", "run_id", "reference", "summary"),
    "AgentCheck": ("id", "run_id", "command", "summary"),
}

REQUIRED_LIST_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "AgentRun": (
        "goal_ids",
        "considered_work",
        "decision_ids",
        "evidence_ids",
        "check_ids",
    ),
}

ENUM_FIELDS_BY_TYPE: dict[str, dict[str, frozenset[str]]] = {
    "AgentRun": {
        "entry_state": frozenset({"new", "red", "green", "review", "blocked"}),
        "target_state": frozenset({"red", "green", "review", "merged", "unblocked"}),
        "result_state": frozenset({"red", "green", "review", "merged", "blocked"}),
    },
    "AgentReading": {
        "subject": frozenset(
            {
                "claude_md",
                "open_issues",
                "open_prs",
                "okf_knowledge",
                "code",
                "tests",
                "ci",
                "other",
            }
        ),
    },
    "AgentGoal": {
        "status": frozenset({"proposed", "active", "achieved", "carried"}),
    },
    "AgentEvidence": {
        "kind": frozenset(
            {
                "test_red",
                "test_green",
                "ci",
                "diff",
                "review",
                "runtime",
                "issue",
                "pr",
                "okf",
                "other",
            }
        ),
    },
    "AgentCheck": {
        "result": frozenset({"passed", "failed", "observed"}),
    },
}

OPTIONAL_FIELDS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "AgentDecision": ("goal_id",),
    "AgentEvidence": ("goal_id",),
    "AgentCheck": ("goal_id", "evidence_id"),
}

AGENT_REPORT_TYPES = frozenset(REQUIRED_TEXT_FIELDS_BY_TYPE)


def declared_fields_for_type(concept_type: str) -> frozenset[str]:
    """Every frontmatter key `concept_type`'s table in `knowledge/okf.schema.sql`
    declares, plus the `type` discriminator okf-parser itself reads."""
    return frozenset(
        {"type"}
        | set(REQUIRED_TEXT_FIELDS_BY_TYPE.get(concept_type, ()))
        | set(REQUIRED_LIST_FIELDS_BY_TYPE.get(concept_type, ()))
        | set(ENUM_FIELDS_BY_TYPE.get(concept_type, {}))
        | set(OPTIONAL_FIELDS_BY_TYPE.get(concept_type, ()))
    )


def unknown_fields_for_type(concept_type: str, frontmatter: dict[str, YamlValue]) -> list[str]:
    """Frontmatter keys `concept_type` carries that its own table in
    `knowledge/okf.schema.sql` never declares.

    `missing_fields_for_type` only ever checks a *declared* field's presence,
    so a renamed or invented key (`title` where the schema says `goal`) can
    slip through undetected by `okf-parser check` (which only validates PK/FK
    catalog metadata, not column names) until it silently changes a
    generated file. This closes that gap at the same check.
    """
    declared = declared_fields_for_type(concept_type)
    return sorted(key for key in frontmatter if key not in declared)


def missing_fields_for_type(concept_type: str, frontmatter: dict[str, YamlValue]) -> list[str]:
    """Names of `concept_type` fields that still violate its round-report contract.

    Mirrors `knowledge/okf.schema.sql`'s table for `concept_type` field for
    field: a required text field must be a non-blank string, a required list
    field must hold at least one entry, and an enum field must hold one of its
    declared values.
    """
    missing: list[str] = []
    for field in REQUIRED_TEXT_FIELDS_BY_TYPE.get(concept_type, ()):
        value = frontmatter.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    for field in REQUIRED_LIST_FIELDS_BY_TYPE.get(concept_type, ()):
        value = frontmatter.get(field)
        if not isinstance(value, list) or not value:
            missing.append(field)
    for field, allowed in ENUM_FIELDS_BY_TYPE.get(concept_type, {}).items():
        value = frontmatter.get(field)
        if value not in allowed:
            missing.append(field)
    return sorted(missing)


def missing_agent_run_fields(frontmatter: dict[str, YamlValue]) -> list[str]:
    """Backward-compatible alias for `missing_fields_for_type("AgentRun", ...)`."""
    return missing_fields_for_type("AgentRun", frontmatter)


def main(argv: list[str] | None = None) -> int:
    from okf_parser.parser import DocumentParseError, parse_document

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        type=Path,
        help=(
            "Path to a single Agent*-typed round-report document, or a "
            "directory to scan recursively for every such document."
        ),
    )
    args = parser.parse_args(argv)

    is_dir = args.path.is_dir()
    files = sorted(args.path.rglob("*.md")) if is_dir else [args.path]

    exit_code = 0
    checked_any = False
    for file in files:
        try:
            frontmatter = parse_document(file).frontmatter
        except DocumentParseError:
            # Plain docs (e.g. a directory's index.md) have no frontmatter at
            # all — okf-parser itself treats those as reserved, not concepts.
            if is_dir:
                continue
            raise
        concept_type = frontmatter.get("type")
        if concept_type not in AGENT_REPORT_TYPES:
            if is_dir:
                continue
            print(
                f"❌ {file} has type {concept_type!r}, "
                f"expected one of {sorted(AGENT_REPORT_TYPES)}."
            )
            return 1

        checked_any = True
        missing = missing_fields_for_type(concept_type, frontmatter)
        unknown = unknown_fields_for_type(concept_type, frontmatter)
        if not missing and not unknown:
            print(f"✅ {file} — {concept_type} round report is complete.")
            continue

        exit_code = 1
        if missing:
            print(f"❌ {file} — {concept_type} round report is still missing:")
            for field in missing:
                print(f"  - {field}")
        if unknown:
            print(
                f"❌ {file} — {concept_type} carries fields not declared in "
                "knowledge/okf.schema.sql:"
            )
            for field in unknown:
                print(f"  - {field}")

    if is_dir and not checked_any:
        print(f"❌ {args.path} contains no Agent*-typed round-report documents.")
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
