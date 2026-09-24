---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-eb5f9r-reading-okf"
run_id: "2026-09-24-exciting-mccarthy-eb5f9r"
subject: "okf_knowledge"
reference: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; knowledge/agent-runs/2026-09-20-exciting-mccarthy-fv62kx/run.md; .claude/hourly-loop.md; .wisk/knowledge/experiences/handoffs/handoff-issue-1471-ia-publish-pending.md"
finding: "Bundle knowledge/ conformante no baseline desta rodada (2031 conceitos, 0 diagnosticos). O relatorio AgentRun mais recente no formato legado e 2026-09-20-exciting-mccarthy-fv62kx (mesclou PR #1590, lote 24 real do segmentador). Depois dele, o git log de main mostra mais duas rodadas ('wisk(run)', commits a914d57 e ad49efc) operadas pelo runtime Wisk -- nao registradas como AgentRun/OKF, ja que .claude/hourly-loop.md determina que o loop horario passou a ser operado exclusivamente pelo Wisk a partir de 2026-09-20 e instrui a nao criar novos AgentRuns nesse loop. O unico handoff Wisk ativo (#1471, IA publish pending) segue bloqueado por credenciais, sem trabalho novo elegivel. `uv run wisk start`/`wisk session next` executados ao vivo nesta rodada nao selecionaram nenhum trabalho (ver reading-prs) apesar de 3 PRs verdes havia 4 dias -- achado novo que nenhuma rodada anterior havia registrado."
---

# Leitura: conhecimento OKF

`uv run okf-parser check knowledge --relational-schema okf.schema.sql`
no inicio desta rodada: `{"conformant": true, "diagnostics": [],
"concept_count": 2031, "markdown_count": 2034, "reserved_count": 3}`.
Bundle limpo, sem lacunas estruturais no formato legado `AgentRun`.

O relatorio mais recente nesse formato,
`2026-09-20-exciting-mccarthy-fv62kx`, fechou a rodada do lote 24 real
do segmentador (#1050, PR #1590 mesclada) e deixou registrado que a
tensao AgentRun-vs-Wisk (dois mecanismos de loop concorrentes no mesmo
repositorio) segue sem reconciliacao do dono humano, ja escalada uma
vez em 2026-09-14, com instrucao explicita de "nao reescalar sem fato
novo".

Fato novo confirmado nesta rodada: entre 2026-09-20 e 2026-09-24 (4
dias), o runtime Wisk produziu duas rodadas adicionais registradas
apenas como commits `wisk(run)` em `main` (nao como `AgentRun`/OKF,
conforme `.claude/hourly-loop.md`), avancando #1050 para
document_count=191 (lotes 25/#1594) e deixando 3 PRs de continuidade
(#1597, #1598, #1599) verdes e prontas. Desde entao, porem, nao houve
nenhuma rodada Wisk nova: `uv run wisk start` retornou
`{"state": "blocked", "blockers": ["no-eligible-session"],
"candidates": []}` e `uv run wisk session next` retornou `null`,
mesmo com um handoff ativo registrado
(`handoffs/handoff-issue-1471-ia-publish-pending`, que permanece
corretamente bloqueado por credenciais) e as 3 PRs verdes acima sem
nenhuma acao. O runtime Wisk parece nao estar selecionando as PRs
prontas como trabalho elegivel neste ambiente/sessao -- ver decision
correspondente sobre como esta rodada tratou esse achado sem tentar
depurar o runtime Wisk em si (fora do escopo desta sessao agendada).
