# CLI

Comando raiz:

```bash
uv run --env-file .env causaganha --help
```

## Comandos

### `db`

```bash
uv run --env-file .env causaganha db init
uv run --env-file .env causaganha db status
```

### `collect`

Coleta intimações via PJe e salva no DuckDB.

```bash
uv run --env-file .env causaganha collect --courts TJRO --start-date 2024-12-15 --end-date 2024-12-15
```

### `archive`

Baixa PDFs das intimações ainda não arquivadas.

- Com `IA_ACCESS_KEY`/`IA_SECRET_KEY`: upload para IA.
- Sem chaves: salva localmente (fallback).

```bash
uv run --env-file .env causaganha archive --limit 10
uv run --env-file .env causaganha archive --limit 3 --dry-run
```

### `analyze`

Baixa PDFs e extrai resultado com LLM (requer `GEMINI_API_KEY`).

```bash
uv run --env-file .env causaganha analyze --limit 5
```

### `score`

Calcula ratings OpenSkill e estatísticas.

```bash
uv run --env-file .env causaganha score --limit 100
```

### `pipeline`

Executa `collect → archive → analyze → score` (com flags para pular etapas).

```bash
uv run --env-file .env causaganha pipeline --courts TJRO --skip-archive
```

