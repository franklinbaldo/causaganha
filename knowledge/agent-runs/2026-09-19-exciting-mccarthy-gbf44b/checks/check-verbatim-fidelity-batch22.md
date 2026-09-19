---
type: AgentCheck
id: "2026-09-19-exciting-mccarthy-gbf44b-check-verbatim-fidelity-batch22"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
command: "uv run python verify_batch22.py (script using segmenter_dataset.store._text_element_to_labels, the same production parser ingest_djen_sample_technique1_batch.py uses)"
result: "passed"
evidence_id: "2026-09-19-exciting-mccarthy-gbf44b-evidence-batch22-ingested"
summary: "All 6 candidates: verbatim_match=True after fixing an NBSP substitution (TJGO/543564741, self-corrected by the subagent) and an unescaped XML ampersand (TJPA/576803379)."
---

# Check: fidelidade verbatim independente, lote 22

Rodado apos os 6 subagentes de anotacao terminarem, antes de qualquer
ingestao real no store. Primeira passada encontrou 2 dos 6 candidatos
com problemas (TJGO/543564741: mismatch NBSP; TJPA/576803379: XML
malformado por `&` nao escapado). Ambos corrigidos e reverificados;
segunda passada confirmou `ALL OK` para os 6.
