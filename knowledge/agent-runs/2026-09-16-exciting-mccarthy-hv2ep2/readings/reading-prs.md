---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-hv2ep2-reading-prs"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
subject: "open_prs"
reference: "list_pull_requests(state=open), franklinbaldo/causaganha, 2026-09-16"
finding: "Only 3 open PRs, matching the pre-session summary: #1550 (docs(wisk) closeout for a different concurrent round, stale, not mine -- left alone), #1528 (docs(agent-run) closeout for round bc9ae6, stale, not mine -- left alone), #1353 (dependabot bump in deployment/relay-cf, out of domain scope -- left alone). No open domain PR for issue #1050 -- confirmed this round is starting fresh work, not resuming a stalled PR, and no concurrent session currently has an open PR competing for the same batch."
---

# Leitura: PRs abertas

`list_pull_requests(state=open)` confirmou apenas 3 PRs abertas, nenhuma
delas de domínio para #1050. Nenhuma colisão de PR aberta detectada antes
de iniciar a seleção de candidatos desta rodada — a única colisão real
encontrada foi em tempo de ingestão (documento TRF6/593231752 já
ingerido por uma sessão concorrente entre o escaneamento inicial do store
e a tentativa de ingestão; ver evidence-batch-ingestion).
