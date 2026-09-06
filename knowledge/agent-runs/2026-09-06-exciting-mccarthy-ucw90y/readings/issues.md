---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-ucw90y-reading-issues"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
subject: "open_issues"
reference: "franklinbaldo/causaganha list_issues(state=OPEN, 25 total) + issue_read on #1168, #1173, #1174, checked 2026-09-06T00:5xZ-01:0xZ"
finding: "25 open issues. #924 (closed by the previous round) is gone from the list, as expected. The web reboot cluster (#1168 parent, #1173 migrate /processo, #1174 migrate /publicacoes) is still open, but its premise has shifted: #1173/#1174 were scoped assuming #1170's staged rollout ('depois de #1170 estar integrada'), and #1170 is now closed as superseded by #1169, which claims to have already migrated /processo and /publicacoes itself. Everything else is unchanged from the previous round's triage and remains correctly deferred for this unattended round: #1136/#1131-1134/#1093 (other web/UX) sit on a shell about to be replaced by whichever reboot PR lands, so building more on the legacy shell now would be wasted; #950/#951 (MCP remote hosting) are live deploy/hosting decisions; #1022/#1011/#985 (TCU/TSE Internet Archive publication) need explicit sign-off for hard-to-reverse public uploads; #1047/#1050-1057/#884/#886/#887 (segmenter roadmap) remain annotation/GPU-heavy and unsuited to an unattended round. Given the owner's explicit, current, in-hand request for adversarial review of PR #1169 (see prs.md reading), that review is the best continuity work available this round — more valuable than triaging #1173/#1174's now-possibly-stale scope, which depends on the outcome of that same review."
---

# Leitura de issues abertas

O cluster do reboot (#1168/#1173/#1174) mudou de premissa desde a rodada anterior: a PR faseada (#1170) que #1173/#1174 assumiam como pré-requisito foi fechada como superseded pela PR única #1169. O restante das 25 issues abertas permanece corretamente fora de escopo desta rodada (web/UX dependente do shell legado, hospedagem MCP, publicações IA que exigem aval explícito, e roadmap do segmentador). O trabalho de maior valor disponível é o pedido explícito e atual do dono para revisar adversarialmente a PR #1169.
