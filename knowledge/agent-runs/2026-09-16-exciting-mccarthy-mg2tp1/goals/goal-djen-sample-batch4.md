---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal: "Run a fourth real batch through scripts/ingest_djen_sample_technique1_batch.py: select the 5 remaining unused, non-TJRO Acordao candidates in the 3 still-unrepresented tribunals with usable candidates (TJSC x1, TRF4 x3, TRF6 x1), clean their raw embedded HTML markup with the existing batch3 cleaner, annotate each with an independent subagent using the canonical Technique 1 prompt, and ingest the ones that pass mechanical/verbatim validation, measurably raising document_count and tribunal diversity beyond today's 81/21."
rationale: "The previous round (uyx7xc, merged PR #1543) proved the ingestion mechanism scales across three real batches (61->68->74->81 documents) and its own next_move explicitly asks for more batches through the same reusable path, prioritizing still-unrepresented tribunals first. This round's own live scan found exactly 3 new tribunals (TJSC, TRF4, TRF6) with usable Sentenca/Acordao candidates left in the sample pool, all needing the same HTML-cleanup treatment the previous round already built and validated -- reusing it unmodified is the lowest-risk way to keep growing the corpus toward RFC 0012's >=30/>=30 per-split floor. No architectural change is justified: the mechanism is already proven, only its known-defect checklist (entity decode, HTML cleanup, dangling-pair overrides) needs to be applied again."
success_signal: "scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing above 81 and 3 new tribunals (TJSC, TRF4, TRF6) present in the store's source.tribunal attribute. uv run pytest -q and ruff check/format stay green with no changes needed to the ingestion script or its test suite (this batch exercises the existing mechanism plus the existing pre-decode/clean-html step, not new production code). A PR is opened documenting the before/after governance numbers and driven to a mergeable state."
status: "achieved"
---

# Goal: quarto lote real multi-tribunal para #1050

Reusar `scripts/ingest_djen_sample_technique1_batch.py` sobre os 5
candidatos reais restantes nos 3 tribunais ainda sem nenhum documento no
store (TJSC, TRF4, TRF6), aplicando o limpador HTML->texto puro ja
validado pela rodada anterior (mesmo defeito: wrapper HTML bruto sem
fechamento), crescendo `document_count` e a diversidade de tribunais em
direcao ao piso de RFC 0012 Sec 5 item 4.
