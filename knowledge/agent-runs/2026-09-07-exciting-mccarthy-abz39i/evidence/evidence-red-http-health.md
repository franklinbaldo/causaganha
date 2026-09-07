---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-abz39i-evidence-red-http-health"
run_id: "2026-09-07-exciting-mccarthy-abz39i"
goal_id: "2026-09-07-exciting-mccarthy-abz39i-goal-fix-pr-1247-http-health"
kind: "test_red"
reference: "uv run pytest -q tests/causaganha_mcp/test_http_health.py on feat/http-public-mcp-profile @ e52566d (unmodified); also reproduced in CI job 101589879832 (run 34071610503, 'tests (tjro)') on the live PR #1247"
summary: "test_health_endpoint_tool_count_matches_canonical_catalog fails with AssertionError: assert 6 == 10. It calls await build_server().list_tools() (causaganha_mcp.server's operator/stdio catalog, 10 tools including the four path-accepting diagnostic tools) and asserts the HTTP /health endpoint reports the same count, but http_server.py in this PR already builds its mcp from causaganha_mcp.profiles.build_public_server() (6 tools) — the two catalogs diverged exactly as the PR intended, and this one test was not updated to match. Confirmed identically both locally (git stash of the fix) and in the PR's own CI run, ruling out a local-environment-only failure."
---

# Evidência RED

`test_health_endpoint_tool_count_matches_canonical_catalog` falha com `assert 6 == 10`: compara `/health` (agora perfil público, 6 tools) contra `build_server()` (perfil de operador, 10 tools). Reproduzido localmente e no log de CI da PR #1247.
