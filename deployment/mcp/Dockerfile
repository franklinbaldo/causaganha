FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

# Pinned to match .github/actions/setup/action.yml's astral-sh/setup-uv version.
RUN pip install --no-cache-dir uv==0.7.22

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Frozen install: the exact dependency graph is resolved once and committed
# as uv.lock (#1614). --frozen fails the build instead of silently
# re-resolving if pyproject.toml and uv.lock ever drift apart.
RUN uv sync --frozen --no-dev --no-editable

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin mcp \
    && chown -R mcp:mcp /app
USER mcp

ARG GIT_SHA=unknown
ENV PATH="/app/.venv/bin:${PATH}" \
    CAUSAGANHA_MCP_HOST=0.0.0.0 \
    CAUSAGANHA_MCP_PORT=8080 \
    CAUSAGANHA_MCP_PATH=/mcp \
    CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS=45 \
    CAUSAGANHA_MCP_MAX_CONCURRENCY=4 \
    CAUSAGANHA_MCP_COMMIT=${GIT_SHA} \
    CAUSAGANHA_WEB_BASE_URL=https://franklinbaldo.github.io/causaganha/

EXPOSE 8080

CMD ["causaganha-mcp-http"]
