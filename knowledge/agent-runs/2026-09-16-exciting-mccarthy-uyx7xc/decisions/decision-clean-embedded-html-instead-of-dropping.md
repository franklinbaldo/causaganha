---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-uyx7xc-decision-clean-embedded-html-instead-of-dropping"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
question: "5 of 7 selected candidates (TJMG, TJRS, TJTO, TRF2, TST) failed ingestion with 'malformed tagged XML' because their texto_limpo retains raw, sometimes-malformed embedded HTML markup (unclosed <br>, a full <html><head>...<body> wrapper) -- a defect independent of anything the annotating subagent does. Prior rounds' established pattern for a newly-discovered defect class was to drop the affected candidates and document the finding for a future round. Should this round follow that same drop-and-document pattern, or attempt a real fix within the round?"
choice: "Write a small ad hoc HTML-to-plain-text cleaner (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py, stdlib html.parser only) and apply it to the 5 affected candidates' texto_limpo before re-annotating, rather than dropping them."
rationale: "A live scan of the full 483-candidate Sentenca/Acordao pool found 114 candidates with the same full <html> wrapper and 63 more with the same stray unmatched </br> -- together ~37% of the entire remaining candidate pool. Dropping every affected candidate one-by-one (as done for the smaller, one-off defects in batch1/batch2) would silently give up on over a third of the future scale-up budget toward RFC 0012's >=30/>=30 per-split floor. The cleaner is small, uses only the standard library, does not touch scripts/ingest_djen_sample_technique1_batch.py or any production code, and was verified end-to-end this round on all 5 affected candidates (each now parses as well-formed XML, re-annotated by a fresh subagent, and ingested successfully). Kept as an evidence artifact rather than committed to scripts/ since it has no test suite yet and this round's TDD scope was the ingestion outcome, not a new production utility -- a future round can decide whether repeated need justifies promoting it into scripts/ with tests."
---

# Decisao: limpar HTML embutido em vez de descartar os candidatos

Um scan ao vivo mostrou que o defeito (markup HTML bruto/malformado em
`texto_limpo`) afeta ~37% do pool restante de candidatos (114 com wrapper
`<html>` completo, 63 com `</br>` solto) -- grande demais para descartar
candidato por candidato como nas rodadas anteriores. Um limpador simples
(so biblioteca padrao) foi escrito, testado e usado para recuperar os 5
candidatos afetados desta rodada, mantido como artefato de evidencia (nao
promovido a `scripts/` ainda, por nao ter suite de testes propria).
