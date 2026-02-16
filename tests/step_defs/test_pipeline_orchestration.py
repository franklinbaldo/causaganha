"""BDD step definitions for pipeline orchestration (scripts/pipeline/run.py).

Tests only pure functions -- no subprocess calls, no file IO.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when


# Ensure the pipeline scripts directory is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts" / "pipeline"))

from run import (
    ALL_STEPS,
    CMD_BUILDERS,
    DATA_STEPS,
    PipelineConfig,
    PipelineState,
    StepResult,
    build_catalog_cmd,
    build_collect_cmd,
    build_consolidate_cmd,
    build_dashboard_cmd,
    build_embed_cmd,
    format_github_output,
    format_github_summary,
    format_pipeline_header,
    format_pipeline_summary,
    format_step_footer,
    format_step_header,
    has_failures,
    make_config,
    parse_step_outputs,
    should_run,
    update_state,
)


FEATURE = "../features/pipeline/09_pipeline_orchestration.feature"


# ==============================================================================
# SCENARIOS  (Tier 1 → Tier 8, matching the feature file)
# ==============================================================================

# ── Tier 1: End-to-end ───────────────────────────────────────


@scenario(FEATURE, "Full pipeline runs all steps")
def test_e2e_full_pipeline() -> None:
    pass


@scenario(FEATURE, "Single job only runs that step")
def test_e2e_single_job() -> None:
    pass


# ── Tier 2: Conditional logic ────────────────────────────────


@scenario(FEATURE, "Data steps always run for job all")
def test_data_steps_run() -> None:
    pass


@scenario(FEATURE, "Catalog always runs for job all")
def test_catalog_always_runs() -> None:
    pass


@scenario(FEATURE, "Catalog runs when explicitly requested")
def test_catalog_explicit() -> None:
    pass


@scenario(FEATURE, "Catalog triggers when upstream added files")
def test_catalog_triggers() -> None:
    pass


@scenario(FEATURE, "Catalog skips when no files and not requested")
def test_catalog_skips() -> None:
    pass


@scenario(FEATURE, "Dashboard always runs for job all")
def test_dashboard_always_runs() -> None:
    pass


@scenario(FEATURE, "Dashboard runs when explicitly requested")
def test_dashboard_explicit() -> None:
    pass


@scenario(FEATURE, "Dashboard triggers when catalog was updated")
def test_dashboard_triggers() -> None:
    pass


@scenario(FEATURE, "Dashboard skips when catalog not updated and not requested")
def test_dashboard_skips() -> None:
    pass


# ── Tier 3: State transitions ────────────────────────────────


@scenario(FEATURE, "Empty initial state")
def test_empty_state() -> None:
    pass


@scenario(FEATURE, "Update state with files_added result")
def test_state_files_added() -> None:
    pass


@scenario(FEATURE, "Update state with catalog_updated result")
def test_state_catalog_updated() -> None:
    pass


@scenario(FEATURE, "State accumulates multiple results")
def test_state_accumulates() -> None:
    pass


@scenario(FEATURE, "State preserves files_added across updates")
def test_state_preserves() -> None:
    pass


@scenario(FEATURE, "No failures in empty state")
def test_no_failures_empty() -> None:
    pass


@scenario(FEATURE, "Detect failure when a step failed")
def test_has_failures_true() -> None:
    pass


@scenario(FEATURE, "No failure when all steps succeed")
def test_has_failures_false() -> None:
    pass


# ── Tier 4: Step ordering ────────────────────────────────────


@scenario(FEATURE, "ALL_STEPS defines the correct execution order")
def test_all_steps_order() -> None:
    pass


@scenario(FEATURE, "DATA_STEPS are the first three steps")
def test_data_steps_order() -> None:
    pass


# ── Tier 5: Command building ─────────────────────────────────


@scenario(FEATURE, "Build collect command with date and tribunal")
def test_collect_cmd_all() -> None:
    pass


@scenario(FEATURE, "Build collect command without optional params")
def test_collect_cmd_minimal() -> None:
    pass


@scenario(FEATURE, "Build consolidate command with specific date")
def test_consolidate_cmd_date() -> None:
    pass


@scenario(FEATURE, "Build consolidate command in backfill mode")
def test_consolidate_cmd_backfill() -> None:
    pass


@scenario(FEATURE, "Build embed command")
def test_embed_cmd() -> None:
    pass


@scenario(FEATURE, "Build catalog command")
def test_catalog_cmd() -> None:
    pass


@scenario(FEATURE, "Build dashboard command")
def test_dashboard_cmd() -> None:
    pass


@scenario(FEATURE, "Build command via registry lookup")
def test_registry_lookup() -> None:
    pass


# ── Tier 6: Configuration ────────────────────────────────────


@scenario(FEATURE, "Build config strips whitespace from date and tribunal")
def test_config_strips_whitespace() -> None:
    pass


@scenario(FEATURE, "Build config with empty optional fields")
def test_config_empty_optionals() -> None:
    pass


# ── Tier 7: Output parsing ───────────────────────────────────


@scenario(FEATURE, "Parse key-value output lines")
def test_parse_kv() -> None:
    pass


@scenario(FEATURE, "Parse empty output")
def test_parse_empty() -> None:
    pass


@scenario(FEATURE, "Parse output with extra whitespace")
def test_parse_whitespace() -> None:
    pass


@scenario(FEATURE, "Parse output preserves values with equals signs")
def test_parse_equals_in_value() -> None:
    pass


# ── Tier 8: Output formatting ────────────────────────────────


@scenario(FEATURE, "Format GitHub Actions output with files added")
def test_format_gh_output() -> None:
    pass


@scenario(FEATURE, "Format GitHub Actions output all false")
def test_format_gh_output_false() -> None:
    pass


@scenario(FEATURE, "Format GitHub summary with catalog link")
def test_format_gh_summary_with_link() -> None:
    pass


@scenario(FEATURE, "Format GitHub summary without catalog link")
def test_format_gh_summary_no_link() -> None:
    pass


@scenario(FEATURE, "Format step header")
def test_format_step_header() -> None:
    pass


@scenario(FEATURE, "Format step footer success")
def test_format_step_footer_success() -> None:
    pass


@scenario(FEATURE, "Format step footer failure")
def test_format_step_footer_failure() -> None:
    pass


@scenario(FEATURE, "Format pipeline header with all options")
def test_format_pipeline_header_all() -> None:
    pass


@scenario(FEATURE, "Format pipeline header without optional fields")
def test_format_pipeline_header_minimal() -> None:
    pass


@scenario(FEATURE, "Format pipeline summary")
def test_format_pipeline_summary() -> None:
    pass


# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def context() -> dict[str, Any]:
    """Shared mutable context passed between Given/When/Then steps."""
    return {}


def _default_config(
    *,
    job: str = "all",
    date: str = "",
    tribunal: str = "",
) -> PipelineConfig:
    """Helper: build a PipelineConfig with test defaults."""
    return make_config(
        job=job,
        date=date,
        tribunal=tribunal,
        proxy_url="https://proxy.test",
        scripts_dir="/scripts",
        repo_root="/repo",
    )


# ==============================================================================
# GIVEN STEPS
# ==============================================================================


@given("a default pipeline configuration", target_fixture="context")
def background_config() -> dict[str, Any]:
    """Background step: create context with a default config."""
    return {"config": _default_config()}


@given(parsers.parse('a config with job "{job}"'))
def config_with_job(context: dict[str, Any], job: str) -> None:
    context["config"] = _default_config(job=job)


@given(parsers.parse('a config with date "{date}" and tribunal "{tribunal}"'))
def config_with_date_tribunal(context: dict[str, Any], date: str, tribunal: str) -> None:
    context["config"] = _default_config(date=date, tribunal=tribunal)


@given("a config with no date and no tribunal")
def config_no_optionals(context: dict[str, Any]) -> None:
    context["config"] = _default_config(date="", tribunal="")


@given(parsers.parse('a config with date "{date}" and no tribunal'))
def config_date_no_tribunal(context: dict[str, Any], date: str) -> None:
    context["config"] = _default_config(date=date, tribunal="")


@given(
    parsers.parse(
        'a config with job "{job}" and date "{date}" and tribunal "{tribunal}"',
    ),
)
def config_full(context: dict[str, Any], job: str, date: str, tribunal: str) -> None:
    context["config"] = _default_config(job=job, date=date, tribunal=tribunal)


@given(parsers.parse('a config with job "{job}" and no date and no tribunal'))
def config_job_no_optionals(context: dict[str, Any], job: str) -> None:
    context["config"] = _default_config(job=job, date="", tribunal="")


@given(
    parsers.parse(
        "a pipeline state with files_added {fa} and catalog_updated {cu}",
    ),
)
def given_state(context: dict[str, Any], fa: str, cu: str) -> None:
    context["state"] = PipelineState(
        results=(),
        files_added=fa == "true",
        catalog_updated=cu == "true",
    )


@given("an empty pipeline state")
def given_empty_state(context: dict[str, Any]) -> None:
    context["state"] = PipelineState()


@given(
    parsers.parse(
        'a step result named "{name}" with output key "{key}" and value "{value}"',
    ),
)
def given_step_result(
    context: dict[str, Any],
    name: str,
    key: str,
    value: str,
) -> None:
    context["step_result"] = StepResult(
        name=name,
        success=True,
        outputs={key: value},
        duration_seconds=0.0,
    )


@given(parsers.parse('raw inputs with date "{date}" and tribunal "{tribunal}"'))
def raw_inputs(context: dict[str, Any], date: str, tribunal: str) -> None:
    context["raw_date"] = date
    context["raw_tribunal"] = tribunal


@given("raw inputs with no date and no tribunal")
def raw_inputs_empty(context: dict[str, Any]) -> None:
    context["raw_date"] = ""
    context["raw_tribunal"] = ""


@given(parsers.parse('step output text with content "{text}"'))
def given_output_text(context: dict[str, Any], text: str) -> None:
    context["raw_text"] = text.replace("\\n", "\n")


@given("step output text that is empty")
def given_output_text_empty(context: dict[str, Any]) -> None:
    context["raw_text"] = ""


@given("a state with one failed step")
def given_state_with_failure(context: dict[str, Any]) -> None:
    failed = StepResult(name="collect", success=False, outputs={}, duration_seconds=0.0)
    context["state"] = update_state(PipelineState(), failed)


@given("a state with one successful step")
def given_state_all_success(context: dict[str, Any]) -> None:
    ok = StepResult(
        name="collect", success=True, outputs={"files_added": "true"}, duration_seconds=0.0
    )
    context["state"] = update_state(PipelineState(), ok)


@given(parsers.parse('a step called "{name}" with command "{cmd_str}"'))
def given_step_name_cmd(context: dict[str, Any], name: str, cmd_str: str) -> None:
    context["step_name"] = name
    context["step_cmd"] = tuple(cmd_str.split())


@given(parsers.parse('a step called "{name}" that succeeded with outputs "{out_str}"'))
def given_step_succeeded(context: dict[str, Any], name: str, out_str: str) -> None:
    context["step_name"] = name
    context["step_success"] = True
    context["step_outputs"] = parse_step_outputs(out_str.replace("\\n", "\n"))


@given(parsers.parse('a step called "{name}" that failed with no outputs'))
def given_step_failed(context: dict[str, Any], name: str) -> None:
    context["step_name"] = name
    context["step_success"] = False
    context["step_outputs"] = {}


# ==============================================================================
# WHEN STEPS
# ==============================================================================


@when("I build a pipeline config")
def when_build_config(context: dict[str, Any]) -> None:
    context["config"] = make_config(
        job="all",
        date=context.get("raw_date", ""),
        tribunal=context.get("raw_tribunal", ""),
        proxy_url="https://proxy.test",
        scripts_dir="/scripts",
        repo_root="/repo",
    )


_TEST_DEADLINE_S = 1200  # fixed value for deterministic assertions


@when("I build the collect command")
def when_build_collect(context: dict[str, Any]) -> None:
    context["cmd"] = build_collect_cmd(context["config"], deadline_s=_TEST_DEADLINE_S)


@when("I build the consolidate command")
def when_build_consolidate(context: dict[str, Any]) -> None:
    context["cmd"] = build_consolidate_cmd(context["config"], deadline_s=_TEST_DEADLINE_S)


@when("I build the embed command")
def when_build_embed(context: dict[str, Any]) -> None:
    context["cmd"] = build_embed_cmd(context["config"], deadline_s=_TEST_DEADLINE_S)


@when("I build the catalog command")
def when_build_catalog(context: dict[str, Any]) -> None:
    context["cmd"] = build_catalog_cmd(context["config"], deadline_s=_TEST_DEADLINE_S)


@when("I build the dashboard command")
def when_build_dashboard(context: dict[str, Any]) -> None:
    context["cmd"] = build_dashboard_cmd(context["config"], deadline_s=_TEST_DEADLINE_S)


@when(parsers.parse('I look up "{name}" in the command builder registry'))
def when_registry_lookup(context: dict[str, Any], name: str) -> None:
    context["cmd"] = CMD_BUILDERS[name](context["config"], deadline_s=_TEST_DEADLINE_S)


@when("I parse the step outputs")
def when_parse_outputs(context: dict[str, Any]) -> None:
    context["parsed"] = parse_step_outputs(context["raw_text"])


@when("I create an empty pipeline state")
def when_create_empty_state(context: dict[str, Any]) -> None:
    context["state"] = PipelineState()


@when("I update the state with the result")
def when_update_state(context: dict[str, Any]) -> None:
    context["state"] = update_state(context["state"], context["step_result"])


@when(
    parsers.parse(
        'I add another result named "{name}" with output key "{key}" and value "{value}"',
    ),
)
def when_add_another_result(
    context: dict[str, Any],
    name: str,
    key: str,
    value: str,
) -> None:
    second = StepResult(name=name, success=True, outputs={key: value}, duration_seconds=0.0)
    context["state"] = update_state(context["state"], second)


@when("I check for failures")
def when_check_failures(context: dict[str, Any]) -> None:
    context["bool_result"] = has_failures(context["state"])


@when("I format the GitHub output")
def when_format_gh_output(context: dict[str, Any]) -> None:
    context["output"] = format_github_output(context["state"])


@when(parsers.parse('I format the GitHub summary for job "{job}"'))
def when_format_gh_summary(context: dict[str, Any], job: str) -> None:
    context["output"] = format_github_summary(job, context["state"])


@when("I format the step header")
def when_format_step_header(context: dict[str, Any]) -> None:
    context["output"] = format_step_header(context["step_name"], context["step_cmd"])


@when("I format the step footer")
def when_format_step_footer(context: dict[str, Any]) -> None:
    context["output"] = format_step_footer(
        context["step_name"],
        success=context["step_success"],
        outputs=context["step_outputs"],
    )


@when("I format the pipeline header")
def when_format_pipeline_header(context: dict[str, Any]) -> None:
    context["output"] = format_pipeline_header(context["config"])


@when("I format the pipeline summary")
def when_format_pipeline_summary(context: dict[str, Any]) -> None:
    context["output"] = format_pipeline_summary(context["state"])


# ==============================================================================
# THEN STEPS
# ==============================================================================


# ── should_run ─────────────────────────────────────────────────


@then("every step in ALL_STEPS should run")
def then_all_steps_run(context: dict[str, Any]) -> None:
    for step in ALL_STEPS:
        assert should_run(step, context["config"], context["state"]), (
            f"should_run({step!r}) returned False for job='all'"
        )


@then(parsers.parse('should_run "{step}" should be {expected}'))
def then_should_run(context: dict[str, Any], step: str, expected: str) -> None:
    result = should_run(step, context["config"], context["state"])
    assert result == (expected == "true"), (
        f"should_run({step!r}) = {result}, expected {expected}"
    )


# ── Step ordering ─────────────────────────────────────────────


@then(parsers.parse("ALL_STEPS should be {csv}"))
def then_all_steps_csv(context: dict[str, Any], csv: str) -> None:
    expected = tuple(s.strip() for s in csv.split(","))
    assert ALL_STEPS == expected


@then(parsers.parse("DATA_STEPS should be {csv}"))
def then_data_steps_csv(context: dict[str, Any], csv: str) -> None:
    expected = tuple(s.strip() for s in csv.split(","))
    assert DATA_STEPS == expected


# ── Config ────────────────────────────────────────────────────


@then(parsers.parse('the config date should be "{expected}"'))
def then_config_date(context: dict[str, Any], expected: str) -> None:
    assert context["config"].date == expected


@then(parsers.parse('the config tribunal should be "{expected}"'))
def then_config_tribunal(context: dict[str, Any], expected: str) -> None:
    assert context["config"].tribunal == expected


@then("the config date should be empty")
def then_config_date_empty(context: dict[str, Any]) -> None:
    assert context["config"].date == ""


@then("the config tribunal should be empty")
def then_config_tribunal_empty(context: dict[str, Any]) -> None:
    assert context["config"].tribunal == ""


# ── Command ───────────────────────────────────────────────────


@then(parsers.parse('the command should include flag "{flag}"'))
def then_cmd_has_flag(context: dict[str, Any], flag: str) -> None:
    cmd: tuple[str, ...] = context["cmd"]
    assert flag in cmd, f"Flag {flag!r} not in {cmd}"


@then(parsers.parse('the command should not include flag "{flag}"'))
def then_cmd_no_flag(context: dict[str, Any], flag: str) -> None:
    cmd: tuple[str, ...] = context["cmd"]
    assert flag not in cmd, f"Flag {flag!r} unexpectedly in {cmd}"


@then(parsers.parse('the command should include flag "{flag}" with value "{value}"'))
def then_cmd_flag_value(context: dict[str, Any], flag: str, value: str) -> None:
    cmd: tuple[str, ...] = context["cmd"]
    assert flag in cmd, f"Flag {flag!r} not in {cmd}"
    idx = cmd.index(flag)
    assert idx + 1 < len(cmd), f"No value after {flag!r} in {cmd}"
    assert cmd[idx + 1] == value, f"Expected {value!r} after {flag!r}, got {cmd[idx + 1]!r}"


@then(parsers.parse('the command should include substring "{fragment}"'))
def then_cmd_substring(context: dict[str, Any], fragment: str) -> None:
    cmd: tuple[str, ...] = context["cmd"]
    assert any(fragment in elem for elem in cmd), (
        f"Substring {fragment!r} not found in any element of {cmd}"
    )


@then("the builder should return a non-empty command tuple")
def then_builder_nonempty(context: dict[str, Any]) -> None:
    assert isinstance(context["cmd"], tuple)
    assert len(context["cmd"]) > 0


# ── Boolean ───────────────────────────────────────────────────


@then(parsers.parse("the failure check should be {expected}"))
def then_failure_check(context: dict[str, Any], expected: str) -> None:
    assert context["bool_result"] == (expected == "true")


# ── Parsed outputs ────────────────────────────────────────────


@then(parsers.parse('parsed key "{key}" should be "{value}"'))
def then_parsed_kv(context: dict[str, Any], key: str, value: str) -> None:
    assert context["parsed"][key] == value


@then("the parsed outputs should be empty")
def then_parsed_empty(context: dict[str, Any]) -> None:
    assert context["parsed"] == {}


# ── State ─────────────────────────────────────────────────────


@then(parsers.parse("the state should have {count:d} results"))
def then_state_count(context: dict[str, Any], count: int) -> None:
    assert len(context["state"].results) == count


@then(parsers.parse("the state files_added should be {expected}"))
def then_state_files(context: dict[str, Any], expected: str) -> None:
    assert context["state"].files_added == (expected == "true")


@then(parsers.parse("the state catalog_updated should be {expected}"))
def then_state_catalog(context: dict[str, Any], expected: str) -> None:
    assert context["state"].catalog_updated == (expected == "true")


# ── Formatted text ────────────────────────────────────────────


@then(parsers.parse('the formatted text should contain "{fragment}"'))
def then_text_contains(context: dict[str, Any], fragment: str) -> None:
    assert fragment in context["output"], f"{fragment!r} not found in:\n{context['output']}"


@then(parsers.parse('the formatted text should not contain "{fragment}"'))
def then_text_not_contains(context: dict[str, Any], fragment: str) -> None:
    assert fragment not in context["output"], (
        f"{fragment!r} unexpectedly found in:\n{context['output']}"
    )
