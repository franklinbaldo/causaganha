---
type: AgentReading
id: "2026-09-11-exciting-mccarthy-njkncp-reading-issues"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
subject: "open_issues"
reference: "GitHub franklinbaldo/causaganha open issues (mcp__github__list_issues, state=OPEN); knowledge/backlog/issue-*.md"
finding: "Listed all 16 open issues via the GitHub MCP tool: #1093, #1057, #1056, #1055, #1054, #1053, #1051, #1050, #1047 (segmenter/training-corpus cluster, blocked on GPU/annotation infra per knowledge/backlog and GitHub issue #1047's own evidence-first roadmap), #1022 (TCU Parquet upload, blocked on missing IAS3_ACCESS_KEY/IAS3_SECRET_KEY -- re-checked live this round with `env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'`, zero matches, confirming knowledge/backlog/issue-1022.md's blocking_reason still holds), #985 (TSE Processual 2026, blocked on Akamai WAF 403 rejecting this runtime's egress to *.tse.jus.br per knowledge/backlog/issue-985.md, last verified by a Wisk-lineage round on 2026-09-10), #951/#950 (MCP remote endpoint, needs an infra/product decision), #887/#886/#884 (segmenter locked-holdout cluster, same infra blocker family as #1047-#1057), identical to the set every round since at least 2026-09-05 has recorded. This is the exact same 16-issue set 8042ey (the immediately preceding round, HEAD e5fee06) recorded as 'all pre-verified blocked, unchanged again this round.' No GitHub-side state change (no new issue, no comment reopening a blocked one, no label change) since 8042ey's reading. Not actionable this round either; none of knowledge/backlog/issue-*.md's unblock_condition entries are met (no IA credentials, no TSE egress fix deployed, no owner reprioritization of #1093/#950/#951)."
---

# Leitura de issues abertas

16 issues abertas no GitHub, mesmo conjunto de toda rodada recente (05/09-10/09). Todas já verificadas como bloqueadas em `knowledge/backlog/issue-*.md`: cluster do segmenter (infra de GPU/anotação), #1022 (credenciais IAS3 ausentes -- reconfirmado nesta rodada via `env`), #985 (WAF Akamai bloqueando `*.tse.jus.br`), #950/#951/#1093 (decisão de produto/priorização do owner). Nenhuma mudança de estado no GitHub desde a leitura de `8042ey`. Não são acionáveis nesta rodada.
