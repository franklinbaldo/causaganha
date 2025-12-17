# FAQ

## Precisa de API key?

- Para **analisar PDFs** (`causaganha analyze`): sim, precisa de `GEMINI_API_KEY`.
- Para **arquivar PDFs** (`causaganha archive`):
  - Internet Archive: precisa de `IA_ACCESS_KEY` e `IA_SECRET_KEY`.
  - Sem IA keys: funciona com armazenamento local (fallback) em `data/pdf_archive/`.

## Como rodar só local (sem IA)?

Não defina `IA_ACCESS_KEY`/`IA_SECRET_KEY` e rode normalmente:

```bash
uv run --env-file .env causaganha archive --limit 10
```

## Onde ficam os dados?

- Banco DuckDB: `data/causaganha.duckdb` (ou `DB_PATH`).
- PDFs arquivados (fallback local): `data/pdf_archive/`.

## Como rodar os testes?

```bash
uv run pytest -q
```

