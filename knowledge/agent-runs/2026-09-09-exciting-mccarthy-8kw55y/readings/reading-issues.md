---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-8kw55y-reading-issues"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
subject: "open_issues"
reference: "https://github.com/franklinbaldo/causaganha/issues?q=is%3Aissue+is%3Aopen"
finding: "17 open issues, identical set to every round since at least obl3ux (2026-09-08): #1093, #1057, #1056, #1055, #1054, #1053, #1051, #1050, #1047, #1022, #1011, #985, #951, #950, #887, #886, #884. Cross-checked each against its cached knowledge/backlog/issue-<n>.md BacklogItem: all 17 have a durable file with status blocked/deprioritized. Categories: ml_data_work (segmenter issues #1047/#1050/#1051/#1053/#1054/#1055/#1056/#1057/#884/#886/#887 -- need GPU training or human annotation, unavailable in this sandbox), credentials (#1011/#1022 -- need IAS3_ACCESS_KEY/IAS3_SECRET_KEY, absent from this session's env, verified again with env | grep -iE 'IAS3|IA_ACCESS|IA_SECRET|ARCHIVE'), infra_decision (#950/#951 -- need a hosting/ops decision from the repo owner), network_access (#985 -- needs live TSE access, previously found to 403), deprioritized_by_owner (#1093 -- issue body explicitly says not an immediate priority). No GitHub-side state change detected for any of the 17 (same numbers, same blocking conditions) versus the last-verified-run recorded in each backlog file, so none are cited as this round's issues_reading source of new work -- confirms Franklin's per-file backlog cache is doing its job of avoiding re-investigation. No new issues opened since the last round's reading."
---

# Leitura de issues abertas

17 issues abertas, todas já registradas em `knowledge/backlog/issue-<n>.md` como bloqueadas/despriorizadas, sem mudança de estado no GitHub desde a rodada anterior. Nenhuma nova issue aberta.
