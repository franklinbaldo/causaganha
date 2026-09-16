---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal: "Run a sixth real batch through scripts/ingest_djen_sample_technique1_batch.py: annotate and ingest 8 real, unused Sentenca candidates spread across 8 already-represented tribunals (TRF5, TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES) -- measurably raising document_count and the RFC 0012 val/test ceiling beyond today's 93/14/14."
rationale: "Six prior rounds today proved the ingestion mechanism scales (61->93 documents) and the immediately prior round (la7bsl) confirmed tribunal diversity is exhausted (25 tribunals, no new tribunal left even under a widened 2500-char filter) and explicitly redirected the next round to keep drawing additional Sentenca/Acordao candidates from already-represented tribunals -- document_count growth, not diversity, is what still raises the RFC 0012 Sec 5 item 4 floor. A live scan of the sample pool confirms 258 unused in-range candidates remain, 161 already XML-clean; this batch picks 8 of the XML-clean ones from the tribunals with the deepest remaining pools, avoiding the HTML-wrapper cleanup step batches 3/4 needed."
success_signal: "scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing above 93. uv run pytest -q and ruff check/format stay green with no changes needed to the ingestion script or its test suite (this batch exercises the existing mechanism, not new production code). A PR is opened documenting the before/after governance numbers and driven to a mergeable state."
status: "achieved"
---

# Goal: sexto lote real multi-tribunal para #1050

Reusar `scripts/ingest_djen_sample_technique1_batch.py` sobre 8
candidatos reais Sentenca nao usados, um por tribunal, entre os
tribunais ja representados com maior oferta remanescente (TRF5, TJMT,
TJRR, TJPA, TRF3, TJRJ, TJPB, TJES). Todos os 8 sao XML-parseaveis no
texto bruto e sem entidades HTML/CRLF, sem necessidade do limpador HTML
das rodadas anteriores.
