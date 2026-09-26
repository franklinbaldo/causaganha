---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-5txmmk-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. O trabalho selecionado (verificacao de identidade via KV_METADATA no rodape Parquet dos artefatos JURIS/DataJud baixados pelo fallback IA de scripts/reconcile_processos.py, fechando o item 3 restante de #1652/TM-16) toca 'No que NAO fazer': nao usa boto3 (fetch continua via httpx), nao remove o lock por item (nao mexe em archive.py de upload), nao usa mark_djen_raw derivado. Toca 'Style': TRY300/TRY301/TRY401 e sem except Exception cego -- reusa SourceDataError, ja o tipo especifico existente no proprio modulo para 'os bytes que temos nao sao utilizaveis', e _quarantine, ja o mecanismo existente para descartar cache invalido. Segue TDD: RED -> GREEN documentado abaixo. Antes de commitar: uv run ruff check, uv run ruff format --check, uv run pytest -q, todos revalidados verdes."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada. O guia não
tem uma seção dedicada a `scripts/reconcile_processos.py` além das
regras gerais de estilo Python (ruff estrito, TDD como fluxo padrão,
exceções específicas em vez de `except Exception` cego) — todas
seguidas pelo trabalho desta rodada.
