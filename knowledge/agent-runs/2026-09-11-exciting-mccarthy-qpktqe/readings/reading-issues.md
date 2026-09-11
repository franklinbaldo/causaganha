---
type: AgentReading
id: "2026-09-11-exciting-mccarthy-qpktqe-reading-issues"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
subject: "open_issues"
reference: "GitHub franklinbaldo/causaganha open issues (mcp__github__list_issues, state=OPEN, perPage=50); knowledge/backlog/issue-*.md; knowledge/backlog/index.md"
finding: "Listed all 16 open issues via the GitHub MCP tool: #1093, #1057, #1056, #1055, #1054, #1053, #1051, #1050, #1047 (segmenter/training-corpus cluster, blocked on GPU/annotation infra), #1022 (TCU Parquet upload, blocked on missing IAS3 credentials -- re-checked live this round with `env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'`, zero matches), #985 (TSE Processual 2026, blocked on Akamai WAF 403 against *.tse.jus.br), #951/#950 (MCP remote endpoint, needs an infra/product decision), #887/#886/#884 (segmenter locked-holdout cluster, same infra blocker family). Identical 16-issue set to every round since 2026-09-05, and each has a corresponding knowledge/backlog/issue-<n>.md with status=blocked/deprioritized and a still-valid blocking_reason. No GitHub-side state change (no new issue, no comment reopening a blocked one, no label change, no new credential in env). Not actionable this round either."
---

# Leitura de issues abertas

16 issues abertas, mesmo conjunto de toda rodada desde 05/09, todas com cache em `knowledge/backlog/issue-<n>.md` confirmando bloqueio válido (infra de GPU/anotação para o cluster do segmenter, credenciais IAS3 ausentes para #1022, WAF Akamai para #985, decisão de produto pendente para #950/#951/#1093). Reconfirmado ausência de credenciais IA via `env`. Nenhuma mudança de estado no GitHub. Não acionáveis nesta rodada.
