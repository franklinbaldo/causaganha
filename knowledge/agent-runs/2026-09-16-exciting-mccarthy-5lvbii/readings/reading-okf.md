---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-5lvbii-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1050.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-14-exciting-mccarthy-to0ars/{run.md,decisions/decision-agentrun-vs-wisk-policy-conflict.md}, knowledge/agent-runs/2026-09-16-exciting-mccarthy-{uyx7xc,zrek2s}/run.md"
finding: "knowledge/agent-runs/index.md and .claude/hourly-loop.md both declare the legacy AgentRun scaffold mechanism deprecated in favor of a new Wisk runtime (.wisk/knowledge/) for the hourly loop; 'do not create new AgentRuns' is stated explicitly. This round's own scheduled prompt still hard-codes the legacy AgentRun scaffold as mandatory, the same conflict round to0ars (2026-09-14) escalated via a proactive notification to the repo owner, deciding to comply with the scheduled prompt as written rather than unilaterally switch mechanisms, since a single unattended round should not decide on its own authority to stop honoring its own stored instructions. At least a dozen AgentRun rounds since then (0iuk22 through zrek2s, all today) made the identical choice without re-escalating, since the situation is unchanged and a repeat notification would be pure noise. knowledge/backlog/issue-1050.md (BacklogItem type, not itself in the deprecated list) is kept current by whichever mechanism last touches issue #1050/#1051 and documents ten numbered risk/defect classes discovered across 11 batches (HTML entities needing html.unescape, embedded raw HTML markup needing a dedicated cleaner, NBSP silently stripped by str.strip() -- fixed in production code, wrong-hash-space dedup, concurrency collisions between simultaneous rounds, and a batch11-specific directory-collision-between-raw-and-tagged-files defect). document_count stood at 117 as of the last recorded batch (10, round imy2ed) before this round started; PR #1562 (batch 11, still open) would bring it to 119 once merged. RFC 0012 Sec 5 item 4's >=30/>=30 val/test floor needs roughly 200 total documents; val/test ceiling is currently 18/18, so #1051 (independent validation-set adjudication) stays correctly deprioritized until the corpus grows further."
---

# Leitura: conhecimento OKF relevante

O conflito AgentRun-vs-Wisk já foi escalado uma vez (to0ars,
2026-09-14) e a decisão tomada então -- cumprir o prompt agendado como
está escrito, sem trocar de mecanismo unilateralmente -- já foi
replicada por uma dúzia de rodadas hoje sem necessidade de nova
notificação, já que a situação não mudou. `knowledge/backlog/issue-1050.md`
documenta 10 classes de risco/defeito encontradas ao longo de 11 lotes
reais e permanece a fonte viva de continuidade da linhagem #1050/#1051,
independente de qual mecanismo a atualiza. `document_count` estava em
117 antes desta rodada (lote 10), com o lote 11 (PR #1562, ainda aberto)
prestes a levá-lo a 119. #1051 segue corretamente despriorizada até o
corpus crescer além do teto atual (18/18) rumo ao piso de >=30/>=30 do
RFC 0012 Seção 5 item 4.
