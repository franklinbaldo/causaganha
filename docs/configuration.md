# Configuration

## Variáveis de ambiente

Recomendado: crie `.env` a partir de `.env.example` e use `uv run --env-file .env ...`.

### Obrigatórias (para análise)

- `GEMINI_API_KEY`: usado para extrair informações do PDF no comando `causaganha analyze`.

### Opcionais (Internet Archive)

- `IA_ACCESS_KEY` / `IA_SECRET_KEY`: se definidas, o comando `causaganha archive` faz upload para o Internet Archive.
- Se **não** estiverem definidas, o `archive` faz armazenamento local (sem API key).

### Paths locais

- `DB_PATH`: caminho do DuckDB (padrão: `data/causaganha.duckdb`).

## Onde os PDFs ficam

- Local (fallback): `data/pdf_archive/<item_id>/<filename>.pdf`
- Internet Archive (se habilitado): `https://archive.org/details/<item_id>`

