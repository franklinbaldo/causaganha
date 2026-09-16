---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Sibling issue #1051 proved the agent-annotation mechanism works; this round (0iuk22) used it for #1050's own work for the first time: scripts/ingest_djen_sample_technique1_batch.py generalizes ingest_juris_technique1_batch.py to ingest real, already-fetched, non-TJRO documents from data/segmenter_samples/*.jsonl, and a first batch of 7 documents across 7 tribunals (TJMT, TJPA, TRF3, TJCE, TJES, TRF5, TJSE) was annotated (Technique 1) and ingested. Kept open (not resolved) because this is one batch, not the full scale-up: document_count moved 61->68, val/test ceiling moved 9->10 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked and now has a proven, reusable ingestion path. A future round should run more batches through scripts/ingest_djen_sample_technique1_batch.py (data/segmenter_samples/*.jsonl still holds ~820 unused real candidates across ~30 tribunals) to keep growing document_count toward ~200 -- see docs/planning/evidence/segmenter-djen-sample-batch1-2026-09-16.json for this round's before/after governance numbers, and docs/planning/evidence/segmenter-per-split-floor-ceiling-2026-09-16.json for why the ceiling is a function of total corpus size, not review coverage. Each batch should also budget for the mechanical-validation dangling-pair rate seen this round (7/7 candidates needed a manually reviewed allowed_unmatched override for a category with no closing cue in the source text -- see the script's --allowed-unmatched-overrides option)."
last_verified_run_id: "2026-09-16-exciting-mccarthy-0iuk22"
last_verified_at: "2026-09-16T01:50:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. A rodada 0iuk22 fez, pela primeira vez, o trabalho real
desta issue (não apenas removeu o motivo para pula-la, como a rodada
anterior tinha feito): `scripts/ingest_djen_sample_technique1_batch.py`
generaliza `ingest_juris_technique1_batch.py` para ingerir documentos reais
ja coletados, de tribunais alem do TJRO, a partir de
`data/segmenter_samples/*.jsonl` (nunca usado ate agora). Um primeiro lote
de 7 documentos (TJMT, TJPA, TRF3, TJCE, TJES, TRF5, TJSE) foi anotado via
Tecnica 1 e ingerido: `document_count` 61->68, teto de val/test 9->10
(`docs/planning/evidence/segmenter-djen-sample-batch1-2026-09-16.json`).

**Por que continua aberta:** um lote de 7 documentos nao encerra o
trabalho de escala — o piso de RFC 0012 §5 item 4 (>=30 val, >=30 teste,
cada um adjudicado) continua exigindo algo perto de 200 documentos totais.
O caminho agora e repetir o mesmo mecanismo (ja provado, reusavel) sobre o
restante de `data/segmenter_samples/` (~820 candidatos reais ainda nao
usados, ~30 tribunais) em rodadas futuras.
