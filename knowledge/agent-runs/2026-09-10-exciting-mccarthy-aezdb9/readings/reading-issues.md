---
type: AgentReading
id: "2026-09-10-exciting-mccarthy-aezdb9-reading-issues"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN) -- 16 open issues; cross-checked against knowledge/backlog/issue-*.md"
finding: "Same 16 open issues as every recent round (#1093, #1057, #1056, #1055, #1054, #1053, #1051, #1050, #1047, #1022, #985, #951, #950, #887, #886, #884). All 16 have a corresponding knowledge/backlog/issue-<n>.md BacklogItem already recorded as blocked/deprioritized: the segmenter cluster (#1047/#1050/#1051/#1053/#1054/#1055/#1056/#1057/#884/#886/#887) needs GPU/annotation infra this sandbox doesn't have; #1022/#950/#951 need an infra decision or IAS3 credentials (confirmed absent from this session's env: `env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'` returns nothing, matching issue-1011.md's/issue-1022.md's prior verification); #985 is blocked on live TSE 403; #1093 is explicitly deprioritized. knowledge/backlog/issue-1011.md still exists for issue #1011 even though #1011 no longer appears in the open-issues list (confirmed via list_issues; the last AgentRun before r3erpr already noted #1011 closed on 2026-09-08/09) -- this is now a stale backlog cache entry for a closed issue, not a currently-open blocker; noted as a housekeeping candidate rather than a goal on its own (a leftover cache file, harmless but inaccurate). No issue in the open list is newly actionable in this sandbox."
---

# Leitura de issues abertas

16 issues abertas, todas já mapeadas em `knowledge/backlog/issue-*.md` como bloqueadas por infraestrutura ausente neste sandbox (GPU/anotação para o cluster do segmenter, credenciais IAS3, TSE 403 ao vivo). `knowledge/backlog/issue-1011.md` ficou órfão -- a issue #1011 já não aparece na lista de abertas, mas o arquivo de cache continua presente.
