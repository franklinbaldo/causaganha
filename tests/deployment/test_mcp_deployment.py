"""Contract tests for the public MCP deployment artifact."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEPLOYMENT = ROOT / "deployment" / "mcp"


def test_mcp_container_runs_canonical_http_entrypoint_with_conservative_limits() -> None:
    dockerfile = (DEPLOYMENT / "Dockerfile").read_text()

    assert 'CMD ["causaganha-mcp-http"]' in dockerfile
    assert "CAUSAGANHA_MCP_HOST=0.0.0.0" in dockerfile
    assert "CAUSAGANHA_MCP_PORT=8080" in dockerfile
    assert "CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS=45" in dockerfile
    assert "CAUSAGANHA_MCP_MAX_CONCURRENCY=4" in dockerfile
    assert "CAUSAGANHA_MCP_COMMIT=${GIT_SHA}" in dockerfile
    assert "CAUSAGANHA_WEB_BASE_URL=https://franklinbaldo.github.io/causaganha/" in dockerfile


def test_mcp_deployment_does_not_bake_source_credentials() -> None:
    deployment_text = "\n".join(
        path.read_text()
        for path in (
            DEPLOYMENT / "Dockerfile",
            DEPLOYMENT / "cloudbuild.yaml",
        )
    )

    forbidden = ("DATAJUD_API_KEY", "IA_ACCESS_KEY", "IA_SECRET_KEY", "Authorization:")
    assert not any(name in deployment_text for name in forbidden)


def test_cloud_build_injects_commit_at_image_build_time() -> None:
    cloudbuild = (DEPLOYMENT / "cloudbuild.yaml").read_text()

    assert "GIT_SHA=${_GIT_SHA}" in cloudbuild
    assert "${_IMAGE}" in cloudbuild


def test_uv_lock_is_committed_for_reproducible_builds() -> None:
    """#1614: the same commit must resolve to the same dependency set.

    `deploy-mcp.yml` already runs `uv sync --frozen`, which fails outright
    against a checkout with no lockfile to anchor it -- so an untracked
    uv.lock is a latent break, not just a missing best practice.
    """
    lockfile = ROOT / "uv.lock"
    assert lockfile.exists(), "uv.lock must be committed, not gitignored"

    gitignore = (ROOT / ".gitignore").read_text()
    assert "uv.lock" not in gitignore.splitlines()


def test_mcp_dockerfile_pins_base_image_by_digest() -> None:
    dockerfile = (DEPLOYMENT / "Dockerfile").read_text()

    from_line = next(line for line in dockerfile.splitlines() if line.startswith("FROM "))
    assert re.fullmatch(r"FROM python:3\.12-slim@sha256:[0-9a-f]{64}", from_line), (
        f"base image must be pinned by digest, got: {from_line!r}"
    )


def test_mcp_dockerfile_installs_from_frozen_lockfile() -> None:
    dockerfile = (DEPLOYMENT / "Dockerfile").read_text()

    assert "COPY pyproject.toml uv.lock" in dockerfile
    assert "uv sync --frozen" in dockerfile
    # The old unpinned, free-resolution install path must be gone.
    assert "pip install --no-cache-dir ." not in dockerfile


def test_mcp_dockerfile_runs_as_non_root_user() -> None:
    dockerfile = (DEPLOYMENT / "Dockerfile").read_text()

    user_lines = [line for line in dockerfile.splitlines() if line.startswith("USER ")]
    assert user_lines, "Dockerfile must switch to a non-root user before CMD"
    assert all(line.strip() != "USER root" for line in user_lines)

    cmd_index = dockerfile.index('CMD ["causaganha-mcp-http"]')
    last_user_index = dockerfile.rindex(user_lines[-1])
    assert last_user_index < cmd_index, "USER must be set before the container's CMD runs"


def test_ci_setup_action_installs_from_frozen_lockfile() -> None:
    """CI must fail closed if pyproject.toml and uv.lock ever drift apart."""
    setup_action = (ROOT / ".github" / "actions" / "setup" / "action.yml").read_text()

    assert "uv sync --frozen" in setup_action or 'uv sync "${args[@]}" --frozen' in setup_action
