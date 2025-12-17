# Getting Started

## Requisitos

- Python 3.11+
- `uv` (gerenciador de dependências)

## Instalação

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv sync --dev
uv pip install -e .
```

## Primeiro run

```bash
cp .env.example .env
# edite .env

uv run --env-file .env causaganha --help
uv run --env-file .env causaganha db init
```

## Pipeline mínimo

```bash
uv run --env-file .env causaganha collect --courts TJRO
uv run --env-file .env causaganha archive --limit 5
uv run --env-file .env causaganha analyze --limit 2
uv run --env-file .env causaganha score --limit 100
```

