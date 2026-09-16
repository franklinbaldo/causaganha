---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-la7bsl-goal-djen-sample-batch5"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
goal: "Run a fifth real batch through scripts/ingest_djen_sample_technique1_batch.py: annotate and ingest 7 real, unused Acordao candidates -- 4 in a genuinely new tribunal (TJMS) surfaced by widening the candidate length filter, plus 3 more in already-represented tribunals (TJPA x2, TJPI x1) -- measurably raising document_count and tribunal diversity beyond today's 86/24."
rationale: "Five prior rounds today proved the ingestion mechanism scales (61->86 documents) and the immediately prior round (mg2tp1) explicitly redirected the next round to widen candidate selection beyond new-tribunal diversity, since only 8 tribunals without usable candidates remained under its 4000-char filter. Widening that filter (2500-18000 chars) both surfaces a previously-missed 25th tribunal (TJMS) and confirms 261 more usable candidates exist in already-represented tribunals, so supply is no longer the constraint. All 7 selected candidates parse cleanly as XML on their raw text with no HTML-cleanup step needed, unlike batches 3/4 -- the lowest-risk, highest-yield slice of the remaining pool to process this round."
success_signal: "scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing above 86 and TJMS present as a new tribunal in the store's source.tribunal attribute alongside TJPA/TJPI gaining additional documents. uv run pytest -q and ruff check/format stay green with no changes needed to the ingestion script or its test suite (this batch exercises the existing mechanism, not new production code). A PR is opened documenting the before/after governance numbers and driven to a mergeable state."
status: "achieved"
---

# Goal: quinto lote real multi-tribunal para #1050

Reusar `scripts/ingest_djen_sample_technique1_batch.py` sobre 7
candidatos reais Acordao nao usados: 4 no tribunal TJMS (novo, so
visivel apos ampliar o filtro de tamanho de candidato) e 3 em tribunais
ja representados (TJPA x2, TJPI x1). Todos os 7 sao XML-parseaveis no
texto bruto, sem necessidade do limpador HTML das rodadas anteriores.
