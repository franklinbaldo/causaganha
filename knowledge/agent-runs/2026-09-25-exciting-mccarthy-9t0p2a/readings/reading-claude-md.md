---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Leitura integral no inicio da rodada. As regras de djen-backup (sync-manifest.parquet, djen_raw vs djen_status, workers checker/downloader/uploader) e a fronteira CSS/Panda nao se aplicam ao trabalho selecionado: o alvo desta rodada e o contrato de saida das tools MCP `publicacoes_buscar`/`decisoes_buscar` (src/causaganha_mcp/tools/), Python puro, sem Parquet/DuckDB/web. Regras de estilo aplicaveis: TRY300/TRY301/TRY401 (nenhum raise novo esperado neste trabalho — apenas novos campos Pydantic e testes), 'nao adicionar validacao para cenarios que nao podem acontecer' (o campo novo e um literal constante, nao uma validacao condicional), e 'nao usar except Exception amplo' (nao aplicavel — nenhum try/except novo). Regra de nao regenerar codigo gerado por OKF (web/src/lib/processoConsultar.gen.ts, src/causaganha_mcp/_generated/domain_models.py) 'para corrigir' relatorios em rascunho confirmada como armadilha a evitar: este run.md ficara com completed_at vazio ate o final da rodada, o que muda temporariamente a forma inferida dos schemas Zod/domain-model gerados — os testes correspondentes so devem voltar a passar quando este relatorio for preenchido, nunca regenerando os arquivos."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme
exigido pelo contrato `AgentRun`. Nenhuma regra do arquivo bloqueia ou
reorienta o trabalho selecionado (contrato de saida do MCP, ver
`goal_ids`); a advertencia sobre os tres testes que falham enquanto este
`run.md` esta em rascunho foi lida e sera respeitada sem regenerar os
arquivos gerados.
