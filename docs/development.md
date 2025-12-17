# Development

## Setup

```bash
uv sync --dev
uv pip install -e .
```

## Tests

```bash
uv run pytest -q
```

## Lint

```bash
uv run ruff check .
```

## Docs (MkDocs)

```bash
uv run mkdocs serve
uv run mkdocs build
```

## Vendoring the PJe OpenAPI spec

For easier iteration on the PJe Comunica API client (schemas, contract tests, type generation), we vendor the OpenAPI definition under `openapi/`.

```bash
uv run python scripts/fetch_pje_openapi.py --output openapi/pje-comunicaapi-v1.openapi.json
```
