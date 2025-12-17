# CausaGanha (v2)

Plataforma (alpha) para coletar intimações do PJe, baixar PDFs, extrair resultados com LLM e calcular rankings de advogados via OpenSkill.

## Documentação

- Comece aqui: `docs/index.md`
- CLI: `docs/cli.md`
- Configuração: `docs/configuration.md`
- Arquitetura: `docs/architecture.md`

## Instalação (local)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv sync --dev
uv pip install -e .
```

## Configuração

Crie `.env` baseado em `.env.example`.

- `GEMINI_API_KEY`: necessário para `analyze` (extração do PDF).
- `IA_ACCESS_KEY` / `IA_SECRET_KEY`: opcionais. Se não estiverem definidos, o `archive` usa armazenamento local (sem API key).

## Uso rápido

```bash
uv run --env-file .env causaganha db init

# 1) coletar (PJe API → DuckDB)
uv run --env-file .env causaganha collect --courts TJRO

# 2) arquivar PDFs (local por padrão; IA se chaves existirem)
uv run --env-file .env causaganha archive --limit 10

# 3) analisar PDFs (requer GEMINI_API_KEY)
uv run --env-file .env causaganha analyze --limit 5

# 4) calcular ratings
uv run --env-file .env causaganha score --limit 100
```

## Desenvolvimento

```bash
uv run pytest -q
uv run ruff check .
```

