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

## API docs (Sphinx)

API docs são opcionais e vivem em `docs/api/`.

```bash
uv run sphinx-build -b html docs/api docs/api/_build
```

