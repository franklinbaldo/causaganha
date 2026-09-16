---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-la7bsl-decision-widen-candidate-length-filter"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
goal_id: "2026-09-16-exciting-mccarthy-la7bsl-goal-djen-sample-batch5"
question: "mg2tp1's next_move explicitly asked this round to widen candidate selection to already-represented tribunals since only 8 tribunals were left without a usable candidate under the 4000-17000 raw-char filter five prior same-day rounds used. Before doing that literally, should this round also re-examine whether the length floor itself (not just tribunal coverage) was an arbitrary constraint hiding real candidates in tribunals already marked unusable?"
choice: "Widen the candidate-mining length filter from 4000-17000 to 2500-18000 raw chars (matching the shortest document already successfully ingested in batch4, 2451 chars post-cleanup), and stop restricting selection to still-unrepresented tribunals now that tribunal diversity alone is nearly exhausted."
rationale: "Lowering the floor to 2500 chars surfaced 4 usable Acordao candidates in TJMS -- a 25th tribunal every prior round's narrower filter had missed entirely and mg2tp1 had explicitly listed as unusable. This is strictly additive: it does not relax any correctness rule (mechanical validation, verbatim fidelity, and the guideline's category rules are unchanged), it only recovers real candidates an arbitrary threshold was excluding without cause -- the guideline's own anchor-density concern is already enforced per-document by the Technique 1 prompt's step-3/step-5 self-check, not by a fixed character floor. The same widened filter also confirmed 261 more unused, in-range candidates exist in already-represented tribunals, so supply is no longer a bottleneck for future rounds. Batch size was kept at 7 documents, matching every prior round's 5-7 document scope, to keep quality control (subagent annotation review, verbatim/mechanical validation) tractable within one round even though supply is now abundant."
---

# Decisao: ampliar o filtro de tamanho de candidato

Descer o piso de 4000 para 2500 caracteres brutos revelou um 25o
tribunal (TJMS) que todas as 5 rodadas anteriores do mesmo dia tinham
classificado como sem candidato usavel, sem violar nenhuma regra de
qualidade (a auto-checagem do prompt Technique 1 ja cobre densidade de
tags por documento). Mantive o tamanho do lote em 7 documentos, dentro
do padrao ja estabelecido pelas rodadas anteriores.
