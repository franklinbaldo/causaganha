---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-ttdopu-decision-fix-docs-now-not-defer-again"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal_id: "2026-09-06-exciting-mccarthy-ttdopu-goal-fix-css-token-boundary-docs"
question: "Fix CLAUDE.md's stale CSS token boundary section this round, or flag it again and defer to a future round as the last four rounds did?"
choice: "Fix it now, as this round's primary code-adjacent deliverable, rather than adding a fifth deferral note."
rationale: "Every prior round that read CLAUDE.md re-derived essentially the same finding (--pico-*/--tinta-* gone, --papel-*/--s-* now compatibility aliases) from scratch, each time judging a UI/UX code slice as higher value and pushing the doc fix to 'a future round'. That pattern has repeated four times with zero net progress on the doc itself, while the cost (each round re-spending investigation budget on the same question, and the live risk of a round proceeding on the wrong architectural model before double-checking) is real and recurring. This round's issue-#1136 investigation already produced the verified facts for free, making the fix nearly costless right now; deferring a fifth time would only guarantee a sixth rediscovery."
---

# Decisão: corrigir a documentação agora, não adiar de novo

A fronteira CSS de `CLAUDE.md` já foi sinalizada como obsoleta por quatro rodadas seguidas, sempre adiada em favor de trabalho de código. Como esta rodada já tinha os fatos verificados ao vivo (efeito colateral da investigação da #1136), o custo de corrigir agora é quase zero e o custo de adiar de novo é uma quinta redescoberta.
