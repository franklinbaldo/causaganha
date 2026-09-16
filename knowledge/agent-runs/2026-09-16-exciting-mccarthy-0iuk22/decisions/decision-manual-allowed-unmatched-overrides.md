---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-0iuk22-decision-manual-allowed-unmatched-overrides"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal_id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
question: "All 7 real Technique 1 annotations failed mechanical validation on first ingestion attempt: each had at least one dangling _inicio (relatorio, custas, honorarios, or capitulo_merito) that _detect_allowed_unmatched does not auto-excuse because it isn't positionally last in the document (a later single-anchor label, e.g. a trailing ref_normativa citation, starts after it) -- same designed behavior ingest_juris_technique1_batch.py's own regression test documents. Should the shared _detect_allowed_unmatched heuristic be changed to auto-excuse more cases, or should this batch supply a manually reviewed override per RFC 0012 Sec 9's 'risk signal, not auto-rejected' principle?"
choice: "Do not change the shared, already-tested _detect_allowed_unmatched heuristic (used by both ingest_juris_technique1_batch.py and this new script). Instead add an --allowed-unmatched-overrides option to scripts/ingest_djen_sample_technique1_batch.py, mirroring the --allowed-unmatched CLI option annotate_second_independent.py already exposes for the same situation, and supply a manually reviewed JSON file for this batch's 7 documents after reading each affected subagent's own stated rationale for why no closing cue exists in the source text."
rationale: "Loosening the shared auto-excuse heuristic (e.g. ignoring nested single-anchor labels when computing 'positionally last') would change accepted/rejected behavior for every existing and future caller, including ingest_juris_technique1_batch.py and the 61 already-ingested TJRO documents, without the kind of validation across the whole corpus that change would deserve -- too large a blast radius for one batch's convenience. The override mechanism is not a new pattern: annotate_second_independent.py already established the same contract (a human/reviewing agent declares the reason deliberately) for the exact same class of problem. Using it here keeps the well-tested mechanical core untouched while still letting a reviewed batch through, and documents (in knowledge/backlog/issue-1050.md) that future batches should budget for this same review step rather than being surprised by it again."
---

# Decisao: nao alterar a heuristica compartilhada, usar override manual revisado

Decisao arquitetural desta rodada: a heuristica de deteccao automatica de
pares pendentes (`_detect_allowed_unmatched`, compartilhada com
`ingest_juris_technique1_batch.py`) permanece intocada. O lote real usa o
mesmo mecanismo de override manual ja estabelecido por
`annotate_second_independent.py`.
