---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-0lqpmv-evidence-green-tests"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
goal_id: "2026-09-25-exciting-mccarthy-0lqpmv-goal-supply-chain-lock-nonroot"
kind: "test_green"
reference: "tests/deployment/test_mcp_deployment.py (8/8), uv run ruff check, uv run ruff format --check"
summary: "Após: (1) `uv lock` gerado e commitado (870KB, 264 pacotes resolvidos, incluindo as dependências git de wisk/opf) e removido de .gitignore; (2) deployment/mcp/Dockerfile reescrito para pinar `python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9` (digest do manifest-list multi-arch da tag 3.12-slim, resolvido ao vivo via Docker Hub registry API), instalar `uv==0.7.22` (mesma versão pinada em .github/actions/setup/action.yml via astral-sh/setup-uv) e rodar `uv sync --frozen --no-dev --no-editable` a partir do lock commitado, e criar+trocar para o usuário não-root `mcp` (uid 10001, shell /usr/sbin/nologin) antes do CMD final; (3) .github/actions/setup/action.yml alterado para `uv sync --frozen \"${args[@]}\"`: uv run pytest -q tests/deployment/test_mcp_deployment.py -- 8/8 verde (3 testes pré-existentes + 5 novos). uv run ruff check: All checks passed. uv run ruff format --check: limpo após `uv run ruff format` no arquivo de teste (só ajuste de aspas). Não foi possível validar com `docker build` real (daemon Docker indisponível no sandbox desta sessão -- confirmado por `docker pull` falhando com 'no such file or directory' em /var/run/docker.sock); a validação ficou nos mesmos moldes estáticos já usados pelos testes pré-existentes deste arquivo (comparação textual do Dockerfile), não em uma prova de build+run real -- limitação documentada, não escondida."
---

# Evidência: GREEN (8/8 testes do arquivo, ruff limpo)
