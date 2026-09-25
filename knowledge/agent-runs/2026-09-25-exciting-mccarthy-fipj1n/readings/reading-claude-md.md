---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-fipj1n-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no início da rodada. O trabalho selecionado (validar mes_ano em ManifestJuris.load_text contra path traversal, issue #1610) fica inteiramente em src/tjro_juris/manifest.py e seus testes — não toca o motor djen-backup/sync-manifest, a fronteira CSS/Panda nem os contratos .qmd. Regras de estilo Python aplicáveis e seguidas: TDD como fluxo padrão (RED com 8+1 testes novos contra a API alvo antes de qualquer mudança de produção; GREEN depois), TRY301 pego pelo próprio ruff (raise dentro do try precisou ser extraído para uma função interna _validate_mes_ano, corrigido), nenhum novo `except Exception` cego introduzido, ruff check/format --check limpos. A seção 'Rules of the road > Correctness' sobre djen_raw/manifest não se aplica (este é o manifesto JURIS, tjro_juris.manifest, não o sync-manifest.parquet do djen-backup)."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no início da rodada, conforme
exigido pelo contrato `AgentRun`. O trabalho desta rodada (validação de
`mes_ano` em `src/tjro_juris/manifest.py`) não intersecta nenhuma das
áreas centrais documentadas no guia (djen-backup, fronteira CSS/Panda,
contratos `.qmd`). As regras gerais de estilo Python (ruff estrito, TDD
como fluxo padrão, TRY301) foram seguidas e verificadas ao vivo.
