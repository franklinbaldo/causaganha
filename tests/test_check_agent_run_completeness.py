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

from scripts.check_agent_run_completeness import (
    AGENT_REPORT_TYPES,
    missing_agent_run_fields,
    missing_fields_for_type,
)


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


# `AgentRun`'s five sibling types (`AgentReading`, `AgentGoal`, `AgentDecision`,
# `AgentEvidence`, `AgentCheck`) carry the exact same kind of unenforced
# `NOT NULL`/`CHECK` contract in `knowledge/okf.schema.sql`, but PR #1144 only
# ever checked `AgentRun`. `missing_fields_for_type` generalizes the checker
# so every round-report type gets the same completeness guarantee.

_COMPLETE_SIBLING_FRONTMATTER: dict[str, dict[str, object]] = {
    "AgentReading": {
        "id": "reading-1",
        "run_id": "run-1",
        "subject": "claude_md",
        "reference": "CLAUDE.md",
        "finding": "something learned",
    },
    "AgentGoal": {
        "id": "goal-1",
        "run_id": "run-1",
        "goal": "do the thing",
        "rationale": "because it matters",
        "success_signal": "the thing is observably done",
        "status": "active",
    },
    "AgentDecision": {
        "id": "decision-1",
        "run_id": "run-1",
        "question": "A or B?",
        "choice": "A",
        "rationale": "A is simpler",
    },
    "AgentEvidence": {
        "id": "evidence-1",
        "run_id": "run-1",
        "kind": "test_green",
        "reference": "tests/test_x.py",
        "summary": "10 passed",
    },
    "AgentCheck": {
        "id": "check-1",
        "run_id": "run-1",
        "command": "uv run pytest -q",
        "result": "passed",
        "summary": "suite green",
    },
}


def test_agent_report_types_cover_all_six_sibling_types() -> None:
    assert AGENT_REPORT_TYPES == {
        "AgentRun",
        "AgentReading",
        "AgentGoal",
        "AgentDecision",
        "AgentEvidence",
        "AgentCheck",
    }


@pytest.mark.parametrize("concept_type", sorted(_COMPLETE_SIBLING_FRONTMATTER))
def test_fully_filled_sibling_type_has_no_missing_fields(concept_type: str) -> None:
    frontmatter = _COMPLETE_SIBLING_FRONTMATTER[concept_type]
    assert missing_fields_for_type(concept_type, frontmatter) == []


@pytest.mark.parametrize("concept_type", sorted(_COMPLETE_SIBLING_FRONTMATTER))
def test_blank_required_text_field_is_reported_missing_for_every_sibling_type(
    concept_type: str,
) -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER[concept_type])
    frontmatter["id"] = "   "
    assert "id" in missing_fields_for_type(concept_type, frontmatter)


def test_agent_reading_rejects_unknown_subject() -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentReading"], subject="not-a-subject")
    assert "subject" in missing_fields_for_type("AgentReading", frontmatter)


def test_agent_goal_rejects_unknown_status() -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentGoal"], status="done")
    assert "status" in missing_fields_for_type("AgentGoal", frontmatter)


def test_agent_evidence_rejects_unknown_kind() -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentEvidence"], kind="vibes")
    assert "kind" in missing_fields_for_type("AgentEvidence", frontmatter)


def test_agent_check_rejects_unknown_result() -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentCheck"], result="maybe")
    assert "result" in missing_fields_for_type("AgentCheck", frontmatter)


def test_agent_decision_has_no_enum_fields_but_still_requires_rationale() -> None:
    frontmatter = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentDecision"], rationale="")
    assert missing_fields_for_type("AgentDecision", frontmatter) == ["rationale"]


# Directory-mode scanning: `main()` given a directory recursively checks every
# recognized `Agent*` document under it, instead of requiring one explicit
# path per file — this is what lets `.github/workflows/okf.yml` validate an
# entire `knowledge/agent-runs/` tree in one CI step.


def _write_concept(path: Path, concept_type: str, fields: dict[str, object]) -> None:
    import yaml

    frontmatter = {"type": concept_type, **fields}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml.safe_dump(frontmatter, sort_keys=False)}---\n\n# fixture\n")


def test_main_over_a_directory_reports_zero_for_a_fully_complete_tree(tmp_path: Path) -> None:
    from scripts.check_agent_run_completeness import main

    _write_concept(tmp_path / "run.md", "AgentRun", _COMPLETE_FRONTMATTER)
    _write_concept(
        tmp_path / "readings" / "claude-md.md",
        "AgentReading",
        _COMPLETE_SIBLING_FRONTMATTER["AgentReading"],
    )
    assert main([str(tmp_path)]) == 0


def test_main_over_a_directory_reports_nonzero_when_any_document_is_incomplete(
    tmp_path: Path,
) -> None:
    from scripts.check_agent_run_completeness import main

    _write_concept(tmp_path / "run.md", "AgentRun", _COMPLETE_FRONTMATTER)
    incomplete_goal = dict(_COMPLETE_SIBLING_FRONTMATTER["AgentGoal"], success_signal="")
    _write_concept(tmp_path / "goals" / "g.md", "AgentGoal", incomplete_goal)
    assert main([str(tmp_path)]) == 1


def test_main_over_a_directory_ignores_non_agent_concept_documents(tmp_path: Path) -> None:
    from scripts.check_agent_run_completeness import main

    _write_concept(tmp_path / "fonte.md", "Fonte", {"nome": "djen"})
    assert main([str(tmp_path)]) == 1  # no Agent* documents found under an all-Fonte tree


def test_main_over_a_directory_skips_frontmatter_less_index_files(tmp_path: Path) -> None:
    """A plain `index.md` (no YAML frontmatter at all) is how okf-parser lets a
    directory carry a reserved, non-concept doc (see `knowledge/index.md` and
    `knowledge/agent-runs/index.md`) — the directory scan must not crash on it."""
    from scripts.check_agent_run_completeness import main

    (tmp_path / "index.md").write_text("# Just a plain doc, no frontmatter\n")
    _write_concept(tmp_path / "run.md", "AgentRun", _COMPLETE_FRONTMATTER)
    assert main([str(tmp_path)]) == 0


def test_main_over_this_rounds_own_report_tree_is_complete() -> None:
    """The round tree this very PR ships under `knowledge/agent-runs/` must
    itself pass the directory-mode check — it is both the fixture and the
    proof that the checker works end to end."""
    from scripts.check_agent_run_completeness import main

    reports_root = REPO_ROOT / "knowledge" / "agent-runs"
    assert main([str(reports_root)]) == 0
