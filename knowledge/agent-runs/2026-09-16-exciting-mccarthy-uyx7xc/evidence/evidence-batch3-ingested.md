---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-uyx7xc-evidence-batch3-ingested"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch3-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch3-overrides.json"
summary: "All 7 selected candidates (TJGO, TJPI, TJMG, TJRS, TJTO, TRF2, TST) ingested successfully via scripts/ingest_djen_sample_technique1_batch.py after (a) pre-decoding HTML entities with html.unescape() per this round's decision, (b) cleaning 5 candidates' raw embedded HTML markup (see evidence-html-markup-defect-found-and-fixed), and (c) a reviewed --allowed-unmatched-overrides entry per candidate for the established dangling-pair defect class (relatorio/custas/honorarios/capitulo_merito/ementa openings with no closing cue in source text -- same class documented by every prior batch). uv run python scripts/segmenter_governance_status.py confirms document_count 74->81, val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication 11->12, and 7 new tribunals now represented (TJGO, TJPI, TJMG, TJRS, TJTO, TRF2, TST), bringing the store to 21 distinct tribunals total (up from 14). No changes to production code (scripts/ingest_djen_sample_technique1_batch.py and its test suite reused as-is, same as prior batches) -- only candidate preprocessing (entity decode + HTML cleanup) done ad hoc in this round's own scratch tooling."
---

# Evidencia: lote 3 ingerido com sucesso

7/7 candidatos selecionados ingeridos apos: decodificar entidades HTML,
limpar markup HTML bruto de 5 candidatos, e declarar overrides revisados
para pares pendentes conhecidos. `document_count` 74->81, teto de
val/test 11->12, 7 tribunais novos (total 21 no store). Nenhum codigo de
producao mudou.
