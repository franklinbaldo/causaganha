---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-0lqpmv-evidence-red-tests"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
goal_id: "2026-09-25-exciting-mccarthy-0lqpmv-goal-supply-chain-lock-nonroot"
kind: "test_red"
reference: "tests/deployment/test_mcp_deployment.py::test_uv_lock_is_committed_for_reproducible_builds, ::test_mcp_dockerfile_pins_base_image_by_digest, ::test_mcp_dockerfile_installs_from_frozen_lockfile, ::test_mcp_dockerfile_runs_as_non_root_user, ::test_ci_setup_action_installs_from_frozen_lockfile"
summary: "uv run pytest -q tests/deployment/test_mcp_deployment.py escrito primeiro contra o estado real anterior à mudança (uv.lock movido para fora do repositório para reproduzir o checkout original, sem lock nunca commitado): 5/8 testes falham pela razão certa -- uv.lock ausente + ainda listado em .gitignore; FROM python:3.12-slim sem digest; Dockerfile sem 'COPY pyproject.toml uv.lock' nem 'uv sync --frozen' (só 'pip install --no-cache-dir .' livre); nenhuma linha USER no Dockerfile; .github/actions/setup/action.yml roda 'uv sync \"${args[@]}\"' sem --frozen. Os 3 testes pré-existentes do arquivo continuam verdes (não regressão)."
---

# Evidência: RED (5/5 novos testes falhando pela razão certa)
