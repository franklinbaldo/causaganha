FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

ARG GIT_SHA=unknown
ENV CAUSAGANHA_MCP_HOST=0.0.0.0 \
    CAUSAGANHA_MCP_PORT=8080 \
    CAUSAGANHA_MCP_PATH=/mcp \
    CAUSAGANHA_MCP_TOOL_TIMEOUT_SECONDS=45 \
    CAUSAGANHA_MCP_MAX_CONCURRENCY=4 \
    CAUSAGANHA_MCP_COMMIT=${GIT_SHA} \
    CAUSAGANHA_WEB_BASE_URL=https://franklinbaldo.github.io/causaganha/

EXPOSE 8080

CMD ["causaganha-mcp-http"]
