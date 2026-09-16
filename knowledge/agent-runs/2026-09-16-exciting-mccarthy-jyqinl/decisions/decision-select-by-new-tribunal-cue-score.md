---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-jyqinl-decision-select-by-new-tribunal-cue-score"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal_id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
question: "data/segmenter_samples/*.jsonl has ~800+ unused real candidates across ~30 tribunals. Given a bounded round, which candidates should batch2 select: more documents from an already-represented tribunal, the single highest cue_score candidates regardless of tribunal, or one candidate per still-unrepresented tribunal?"
choice: "Select exactly one Sentença candidate per tribunal not yet in the store (TJBA, TJGO, TJMA, TJPB, TJRJ, TJRN, TJRR, TJTO), each with a high cue_score (>=6, rare categories: preliminar/honorarios/custas/relatorio/ementa/acordao_decisorio) and a manageable length (5-16k characters), rather than piling multiple documents onto one already-represented tribunal or picking the single globally highest-scoring documents wherever they happen to be."
rationale: "#1050's own acceptance criterion is explicitly 'multiple tribunals/sources', not just more documents -- maximizing tribunal diversity per batch is the more direct fit for that criterion than maximizing per-document cue_score within a smaller set of tribunals. Only Sentença/Acórdão are supported by the current v7.1 guideline's document_type_hint (scripts/ingest_djen_sample_technique1_batch.py's _DOCUMENT_TYPE_MAP), and Acórdão candidates found in the same scan were either lower cue_score or excessively long for this batch's size, so all 8 selected are Sentença. Capping length below ~16k characters keeps each subagent's verbatim-reproduction task tractable (the STM candidate found in the same scan was 160k characters, clearly impractical for one subagent's context and out of scope for this batch)."
---

# Decisao: um candidato por tribunal novo, nao mais documentos no mesmo tribunal

Diversidade de tribunal (criterio explicito de #1050) prevalece sobre
maximizar `cue_score` por documento dentro de poucos tribunais. Os 8
candidatos selecionados sao todos `Sentença` (unico tipo com
`document_type_hint` vetted na guideline v7.1) com `cue_score>=6` e
tamanho entre 5-16k caracteres.
