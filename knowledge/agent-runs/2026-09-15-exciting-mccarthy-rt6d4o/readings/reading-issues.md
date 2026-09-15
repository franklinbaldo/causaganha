---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-rt6d4o-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
subject: "open_issues"
reference: "GitHub issues #1469, #1468 (franklinbaldo/causaganha, lidas via mcp__github__issue_read em 2026-09-15)"
finding: "Issue #1469 ('unificar escrita normalizada e leitura compatível no site', filha de #1468) tem 10 critérios de aceite; 4 já satisfeitos por rodadas anteriores (unificação exporter.py/consolidate.py via PR #1473; ORDER BY numero_processo-first; normalização CNJ 20-digitos condicional; ZSTD+ROW_GROUP_SIZE 122880 pinado via PR #1493) e 6 seguem abertos, entre eles o critério textual exato: 'Em web/src/lib/processoCnj.ts, usar igualdade direta somente se todos os arquivos DJEN da busca declararem a capacidade. Arquivos mistos/antigos ou leitores sem suporte mantêm o caminho compatível.' Verifiquei ao vivo que processoCnj.ts (buildDjenSql) ainda usa só regexp_replace(numero_processo, ...) = ? incondicionalmente -- nenhuma leitura de footer, nenhuma ramificação de igualdade direta existe hoje no arquivo. Issue #1468 (pai) lista 'Implementação compatível incorporada e validada' como item 1 do checklist de conclusão -- ainda sem instância de rollout via publicação real (item 4, bloqueado por credenciais IA em #1472, inalterado). Único PR aberto no repo é #1353 (dependabot, stale desde 09/09, sem relação com domínio)."
---

# Leitura de issues abertas

Chamei `mcp__github__list_issues` (22 issues abertas, ordenadas por updated_at) e depois `issue_read` completo em #1469 e #1468 -- as duas mais recentemente tocadas e mais maduras (epic Parquet nativo por CNJ). Confirmei contra o código atual (grep + leitura de web/src/lib/processoCnj.ts) que o critério de igualdade direta de #1469 realmente não foi implementado: `buildDjenSql` não tem parâmetro nem lógica de decisão, e não há leitura de `parquet_kv_metadata` em lugar nenhum do frontend (`web/src/`). As demais issues abertas de topo (segmenter #1047-#1057, #884, dados TCU/TSE #1022/#985, MCP remoto #950/#951) não têm PR nem trabalho em andamento nesta janela e não competem com a continuidade de #1469.
