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
