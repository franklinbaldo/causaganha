---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal: "Run a second real batch through scripts/ingest_djen_sample_technique1_batch.py: select >=1 new, unused, non-TJRO candidate document per new tribunal from data/segmenter_samples/*.jsonl, annotate each with an independent subagent using the canonical Technique 1 prompt, and ingest the ones that pass mechanical/verbatim validation, measurably raising document_count and the RFC 0012 Sec 5 item 4 val/test ceiling beyond today's 68/10/10."
rationale: "The previous round (0iuk22, merged PR #1537) proved the ingestion mechanism works end-to-end (batch1: 61->68 documents, val/test ceiling 9->10) and its own next_move explicitly asked for more batches through the same reusable path, since ~820 unused real candidates across ~30 tribunals still sit in data/segmenter_samples/*.jsonl and the RFC 0012 per-split floor (>=30 val, >=30 test) needs roughly 200 total documents to become reachable. This round found 18 further untouched tribunals with real, cue-scored candidates ready to annotate -- the natural, lowest-risk continuation of an already-proven mechanism, not a new architectural bet."
success_signal: "scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing above 68 and source.tribunal diversity growing beyond the 8 tribunals already in the store (TJRO + the 7 from batch1). uv run pytest -q and ruff check/format stay green with no changes needed to the ingestion script or its test suite (this batch exercises the existing mechanism, not new code). A PR is opened documenting the before/after governance numbers and merged."
status: "in_progress"
---

# Goal: segundo lote real multi-tribunal para #1050

Reusar o mecanismo ja provado pela rodada anterior
(`scripts/ingest_djen_sample_technique1_batch.py`) sobre candidatos reais
de 8 tribunais ainda sem nenhum documento no store, crescendo
`document_count` e o teto de val/test em direcao ao piso de RFC 0012 Sec 5
item 4.
