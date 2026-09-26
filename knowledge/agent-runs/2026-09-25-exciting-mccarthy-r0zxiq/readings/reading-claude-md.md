---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-r0zxiq-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no início da rodada. O trabalho selecionado (fechar o gap write+read de KV_METADATA do TM-04 para `datajud`, em `src/datajud/archive.py`, `src/causaganha/processos/service.py` e `web/src/lib/processoCnj.ts`) não toca djen-backup/manifest nem os contratos `.qmd`, mas toca diretamente a seção 'Style' (ruff estrito, `uv run ruff check`/`format --check` confirmados limpos nos arquivos tocados; nenhum `except Exception` novo introduzido) e a fronteira Python/TS (mesma política duplicada intencionalmente nos dois runtimes, padrão já usado por djen/juris). TDD seguido: testes novos escritos primeiro contra a API alvo (kwarg `tribunal` ainda inexistente em `write_capa_parquet`/`write_movimentos_parquet`), confirmados RED (`ImportError: cannot import name 'DATAJUD_SCHEMA_VERSION'`), depois GREEN após a mudança de produção em Python e TS."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada. O trabalho desta
rodada toca `src/datajud/archive.py`, `src/datajud/service.py`,
`src/causaganha/processos/service.py` e `web/src/lib/processoCnj.ts` (mais
os testes correspondentes) — não há regra específica de `datajud` no guia
além das gerais de estilo (ruff estrito, TDD como fluxo padrão), ambas
seguidas e verificadas (`uv run ruff check`/`format --check` limpos;
RED confirmado antes da implementação em Python e TS).
