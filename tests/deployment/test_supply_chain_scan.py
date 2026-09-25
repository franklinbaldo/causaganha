"""Contract tests for the supply-chain vulnerability scan + SBOM CI gate (#1614/TM-10).

`uv.lock` reproducibility and the MCP Dockerfile's digest pin / non-root user
are covered by test_mcp_deployment.py. This file covers the remaining TM-10
gap: a scanner (`pip-audit`) run against the dependency set actually shipped
in the MCP image, plus a preserved SBOM -- both wired into CI so they run on
every pull request, not just at manual deploy time.
"""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "test.yml"


def _supply_chain_job() -> dict:
    workflow = yaml.safe_load(CI_WORKFLOW.read_text())
    jobs = workflow["jobs"]
    assert "supply-chain" in jobs, (
        "test.yml must define a 'supply-chain' job so the scan/SBOM gate "
        "runs on every pull request, not only at manual deploy time"
    )
    return jobs["supply-chain"]


def _step_runs(job: dict) -> list[str]:
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def test_pip_audit_is_a_dev_dependency() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert "pip-audit" in pyproject


def test_supply_chain_job_exists_in_pull_request_ci() -> None:
    _supply_chain_job()


def test_supply_chain_job_scans_the_dependency_set_actually_shipped() -> None:
    """The MCP Dockerfile installs `--no-dev`; the scan must audit that same
    set, not the full dev environment (which includes doc-tooling deps this
    project doesn't ship, e.g. mkdocs-material's transitive pymdown-extensions
    pin -- see docs/SECURITY_THREAT_MODEL.md TM-10 for the documented split)."""
    runs = "\n".join(_step_runs(_supply_chain_job()))

    assert "uv export" in runs
    assert "--no-dev" in runs
    assert "pip-audit" in runs


def test_supply_chain_job_fails_closed_on_known_vulnerabilities() -> None:
    runs = "\n".join(_step_runs(_supply_chain_job()))
    # pip-audit's default exit code (1 on findings) must not be swallowed by
    # `|| true` or similar -- a scan that can never fail is not a gate.
    assert "|| true" not in runs
    assert "continue-on-error" not in yaml.dump(_supply_chain_job())


def test_supply_chain_job_preserves_an_sbom_artifact() -> None:
    job = _supply_chain_job()
    runs = "\n".join(_step_runs(job))

    assert "cyclonedx-json" in runs

    upload_steps = [
        step
        for step in job.get("steps", [])
        if str(step.get("uses", "")).startswith("actions/upload-artifact")
    ]
    assert upload_steps, "SBOM must be preserved as a build artifact"
