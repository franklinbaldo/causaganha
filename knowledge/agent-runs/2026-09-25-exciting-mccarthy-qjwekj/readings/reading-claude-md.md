---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-qjwekj-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. O trabalho selecionado (embutir causaganha.schema_version/causaganha.item_id no rodape KV_METADATA dos exports Parquet de tjro_juris.service._rows_to_parquet, fechando parte do gap documentado em TM-04) toca diretamente a secao 'Style' (ruff estrito, TRY300/TRY301/TRY401, sem except Exception cego -- nenhum bloco de excecao novo introduzido) e nao toca djen-backup/manifest, a fronteira CSS/Panda nem os contratos .qmd. Nao ha regra especifica de tjro_juris no guia alem das gerais. TDD seguido: 2 testes novos escritos primeiro contra a API alvo (item_id ainda inexistente em _rows_to_parquet), confirmados RED (ImportError/TypeError), depois GREEN apos a mudanca de producao. uv run ruff check/format --check limpos nos arquivos tocados."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada, conforme
exigido pelo contrato `AgentRun`. O trabalho desta rodada fica em
`src/tjro_juris/service.py` e seus testes — nenhuma das arquiteturas
centrais do guia (djen-backup/manifest, fronteira CSS/Panda, contratos
`.qmd`) se aplica diretamente, mas as regras gerais de estilo Python
(ruff estrito, TDD como fluxo padrão) foram seguidas e verificadas.
