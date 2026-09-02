"""Contract tests for the public MCP deployment artifact."""

from __future__ import annotations

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
