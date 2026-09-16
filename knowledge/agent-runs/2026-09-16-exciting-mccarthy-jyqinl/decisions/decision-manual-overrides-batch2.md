---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-jyqinl-decision-manual-overrides-batch2"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal_id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
question: "TJRJ, TJMA and TJBA's annotations each have one or more dangling start/end pairs (capitulo_merito, and for TJBA also custas/honorarios) that _detect_allowed_unmatched does not auto-excuse. Inspecting each: is this the same genuine no-closing-cue situation the previous round (0iuk22) already established a reviewed-override precedent for, or a new class of problem needing a different fix?"
choice: "Same precedent: inspected each dangling pair's actual context in the tagged text (grep) and confirmed each is a single-sentence clause ('Decido.', 'Custas recolhidas.', 'Sem honorários.') that opens a region with no delimiting closing phrase before the next anchor -- identical in kind to batch1's documented dangling relatorio/custas/honorarios/capitulo_merito cases. Supplied a manually reviewed --allowed-unmatched-overrides JSON (docs/planning/evidence/segmenter-djen-sample-batch2-overrides.json) with a specific reason per (document, category) pair, reusing the same mechanism rather than inventing a new one."
rationale: "annotate_second_independent.py and ingest_djen_sample_technique1_batch.py already established this exact contract in the previous round: a human/reviewing agent judges and declares the reason deliberately for a dangling pair the shared heuristic can't safely auto-excuse, rather than loosening that heuristic's blast radius for every caller. Re-deriving the same judgment independently (grep + read context) instead of copying the previous round's reasons verbatim keeps the review honest per document, while the mechanism itself stays exactly as-is -- no code change needed for this class of skip."
---

# Decisao: reusar o mecanismo de override manual do lote 1 para os pares pendentes do lote 2

TJRJ (`capitulo_merito`), TJMA (`capitulo_merito`) e TJBA (`capitulo_merito`,
`custas`, `honorarios`) sao a mesma classe de problema ja resolvida pela
rodada anterior: clausulas terminais sem cue de fechamento explicito.
Override manual revisado aplicado via o mesmo mecanismo
(`--allowed-unmatched-overrides`), sem alterar o codigo de validacao
mecanica compartilhado.
