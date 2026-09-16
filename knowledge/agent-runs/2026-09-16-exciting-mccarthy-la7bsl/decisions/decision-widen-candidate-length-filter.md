---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-la7bsl-decision-widen-candidate-length-filter"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
decision: "Widen the candidate-mining length filter from the 4000-17000 raw-char range five prior same-day rounds used to 2500-18000 chars, and stop restricting selection to still-unrepresented tribunals now that the previous round found only 8 tribunals left without a usable candidate under the narrower filter."
reason: "mg2tp1's own next_move explicitly asked the next round to widen selection to already-represented tribunals since tribunal diversity was nearly exhausted, but a live re-scan first checked whether the length floor itself (not just tribunal coverage) was the real constraint. Lowering the floor to 2500 chars (matching the shortest documents already successfully ingested in batch4, e.g. 2451 chars post-cleanup) surfaced 4 usable Acordao candidates in TJMS -- a 25th tribunal every prior round's narrower filter had missed entirely and mg2tp1 had listed as unusable. This is strictly additive: it does not relax any correctness rule (mechanical validation, verbatim fidelity, and the guideline's category rules are unchanged), it only recovers real candidates the previous filter's arbitrary threshold was excluding without cause. The same widened filter also confirmed 261 more unused, in-range candidates exist in already-represented tribunals, so supply is no longer a bottleneck for future rounds either."
alternatives_considered: "(1) Keep the 4000-char floor and only pick from already-represented tribunals per mg2tp1's literal instruction -- rejected because it would have missed the newly-discovered TJMS tribunal for no principled reason (the guideline's only length concern is anchor-count sanity, which the prompt's own step-3/step-5 self-check already enforces per-document, not a fixed char threshold). (2) Pick a much larger batch (15-20 documents) now that supply is confirmed abundant -- rejected for this round to keep quality control (subagent annotation review, verbatim/mechanical validation) tractable within one round, consistent with every prior batch's 5-7 document scope."
---

# Decisao: ampliar o filtro de tamanho de candidato

Descer o piso de 4000 para 2500 caracteres brutos revelou um 25o
tribunal (TJMS) que todas as 5 rodadas anteriores do mesmo dia tinham
classificado como sem candidato usavel, sem violar nenhuma regra de
qualidade (a auto-checagem do prompt Technique 1 ja cobre densidade de
tags por documento). Mantive o tamanho do lote em 7 documentos, dentro
do padrao ja estabelecido pelas rodadas anteriores.
