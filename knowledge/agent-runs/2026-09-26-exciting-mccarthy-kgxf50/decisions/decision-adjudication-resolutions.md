---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-kgxf50-decision-adjudication-resolutions"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
question: "For each of the 3 documents, the first (batch1) and second (this round's independent haiku) annotations disagreed on several spans -- which final_labels should the accepted ReviewRecord adopt?"
choice: "Per document, kept whichever annotation's tag was more complete/correct against the guideline and mechanically valid, combining the best of both rather than picking one annotation wholesale: TJSC adopted B's cabecalho tags (A omitted cabecalho) and B's acordao_decisorio_fim/resultado split (A merged both into one span, omitting the required resultado tag), plus A's custas_inicio (B omitted it). TJMG adopted B's shorter cabecalho spans plus its separate ref_processual tag (A merged the case number into one long span and never tagged ref_processual), A's fundamentacao_legal classification for the arts. 321/485 citation (matches the guideline's own example shape better than B's bare ref_normativa), and A's closed encerramento pair (B left it unmatched). TJSE adopted A's cabecalho and custas/honorarios tags (B omitted all three) and A's acordao_decisorio_fim for the final citation -- NOT B's fundamentacao_legal reclassification of that same span, which would have reproduced content already deliberately avoided per a pre-existing repo precedent (see decision below) -- plus B's shorter ementa_fim/acordao_decisorio_inicio anchors and B's resultado tag (A never tagged resultado at all)."
rationale: "RFC 0012 doesn't ask a reviewer to prefer one annotator wholesale; it asks for the correct final_labels, verified mechanically and checked against the guideline. Every adopted choice traces to a concrete guideline rule (Rule 1: anchor spans are short, favoring B's tighter cabecalho/ementa/acordao_decisorio_inicio spans over A's longer ones; the ref_processual/resultado categories' own definitions, both of which A omitted entirely in 2 of the 3 documents -- a real completeness gap, not a stylistic one) rather than a coin flip. Every final resolution was independently re-verified for verbatim fidelity and 0 mechanical-validation problems before being trusted (see evidence-mechanical-verification)."
---

# Decision: per-span adjudication across 3 documents

Neither annotation was uniformly better; each round's annotator omitted a
required category in at least one document (A never tagged
`ref_processual`/`resultado` in 2 documents; B omitted `cabecalho` or
`custas`/`honorarios` entirely in 2 documents). The resolution combines
the more complete/correct span from each disagreement, verified against
the guideline's own rules and re-checked mechanically before ingestion.
