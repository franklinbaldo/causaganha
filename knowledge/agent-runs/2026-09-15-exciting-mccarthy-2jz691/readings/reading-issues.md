---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2jz691-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN, orderBy=UPDATED_AT desc)"
finding: "22 issues abertas. A mais recentemente atualizada (2026-09-15T08:56:06Z, antes do início desta rodada) é #1051 'segmenter: build an independently annotated validation set for model selection' -- continuação direta da linhagem de rodadas desta manhã (50ns70..7drjlg, PRs #1493-#1509) que vem escalando ReviewRecords via RFC 0012. #1469 (unificar escrita/leitura Parquet/CNJ) teve seus 3 comentários mais recentes (03:46, 04:40, 06:49) confirmando que TODOS os critérios de aceite que não dependem de publicação real no Internet Archive já foram fechados nesta linhagem (normalização CNJ, ORDER BY, ZSTD+ROW_GROUP_SIZE 122880, certificação de rodapé, igualdade direta em processoCnj.ts, ordem física em reconcile_processos.py, custo de inspeção medido, índice de cobertura confirmado desnecessário com dado real). #1470 (auditoria do catálogo) também fechado por PR #1499/#1500. Resta apenas #1472 (publicação real/rollout), bloqueado desde 11/09 por falta de IA_ACCESS_KEY/IA_SECRET_KEY nesta sandbox -- confirmado ainda ausente (ver leitura seguinte). #1482 (CORS) já mesclado (PR #1484/#1491). Demais issues (#950, #1022, #985, #951, #1093, #1057, #1056, #1055, #1054, #1047, #1053, #1050, #884, #887, #886) são backlog de longo prazo sem sinal de urgência nova."
---

# Leitura: issues abertas

Confirmado: o cluster Parquet/CNJ (#1468/#1469/#1470/#1471) está esgotado no que não depende de credenciais IA -- não resta trabalho de domínio desbloqueado ali. #1051 continua sendo a única frente de domínio real, ativa e desbloqueada nesta sandbox (sem depender de segredos externos), com meta observável (RFC 0012 §5.4: >=30 documentos de validação e >=30 de teste adjudicados) ainda longe de ser atingida (review_count=8 no início desta rodada). Escolho continuar escalando #1051 pelo mesmo motivo que as últimas 4 rodadas: é o único trabalho real, mensurável e não bloqueado disponível.
