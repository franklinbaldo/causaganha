---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-cdee4f-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-cdee4f"
subject: "open_issues"
reference: "GitHub issues #1469, #1470 (franklinbaldo/causaganha, lidas via mcp__github__issue_read em 2026-09-15)"
finding: "Issue #1469 ('unificar escrita normalizada e leitura compatível no site', filha de #1468) tem 10 critérios de aceite; 7 já satisfeitos por rodadas anteriores de hoje e de rodadas passadas (unificação exporter.py/consolidate.py via PR #1473; ORDER BY numero_processo-first; normalização CNJ 20-dígitos condicional; ZSTD+ROW_GROUP_SIZE 122880 pinado via PR #1493; footer causaganha.layout/cnj_normalization; igualdade direta condicional em processoCnj.ts via PR #1495; falhas de fonte degradam para 'compatível', nunca propagam como ausência). Verifiquei ao vivo (leitura de scripts/reconcile_processos.py) que o critério textual exato 'Explicitar ordem física e grupos na escrita do índice em scripts/reconcile_processos.py' segue aberto: a query _INDICE_SQL já tem `ORDER BY numero_processo, fonte` mas o COPY final (`COPY indice_processual TO ... (FORMAT PARQUET, COMPRESSION ZSTD)`) não fixa ROW_GROUP_SIZE explicitamente (depende do default implícito do DuckDB) e não documenta a intenção de pruning por row-group como exporter.py já faz. Issue #1470 (auditoria do catálogo) permanece com linha de base de 11/09, sem novo comentário de reexecução -- não é o gargalo desta rodada. Único PR aberto no repo é #1353 (dependabot, stale)."
---

# Leitura de issues abertas

`mcp__github__list_issues` (22 issues abertas) seguido de `issue_read` completo em #1469 e #1470, as duas mais recentemente tocadas do epic #1468 (Parquet nativo por CNJ). Confirmei contra o código atual que, dos 10 critérios de aceite de #1469, só um permanece genuinamente não implementado e sem PR em voo: a ordem física/grupos explícita na escrita de `indice_processual.parquet` em `scripts/reconcile_processos.py` -- o mesmo padrão que exporter.py já aplica para `comunicacoes.parquet`/`processos.parquet`. As demais issues abertas de topo (segmenter #1047-#1057, #884, dados TCU/TSE, MCP remoto) não têm PR nem trabalho em andamento e não competem com essa continuidade.
