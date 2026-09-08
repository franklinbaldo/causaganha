---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-k18r9l-adr-reading-issues"
run_id: "2026-09-08-exciting-mccarthy-k18r9l-adr"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN, perPage=50)"
finding: "Same 17 open issues as every round earlier today, re-verified fresh: all pre-verified blocked on external inputs (GPU/annotation infra for the segmenter roadmap, IA S3 credentials, a live TSE endpoint, or an infra-hosting decision from the repo owner). No new issues. This round's work (the except-Exception/BLE001 architectural decision) is not itself tracked by any of these issues -- it is a cross-round backlog item that lived only in prior AgentRun next_move fields, triggered this round by explicit live user direction rather than the issue queue."
---

# Reading: open GitHub issues

Mesma fila de 17 issues bloqueadas, sem novidade. O trabalho desta rodada (decisao ADR sobre except Exception) nao esta rastreado como issue -- veio de leads acumulados em rodadas anteriores e de instrucao direta do usuario.
