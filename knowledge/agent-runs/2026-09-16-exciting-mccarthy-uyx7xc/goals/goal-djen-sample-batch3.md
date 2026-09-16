---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal: "Run a third real batch through scripts/ingest_djen_sample_technique1_batch.py: select one new, unused, non-TJRO Sentenca/Acordao candidate per still-unrepresented tribunal with usable candidates (TJGO, TJMG, TJPI, TJRS, TJTO, TRF2, TST), pre-decoding any HTML entities in texto_limpo per the previous round's finding, annotate each with an independent subagent using the canonical Technique 1 prompt, and ingest the ones that pass mechanical/verbatim validation, measurably raising document_count and the RFC 0012 Sec 5 item 4 val/test ceiling beyond today's 74/11/11."
rationale: "The previous round (jyqinl, merged PR #1539) proved the ingestion mechanism scales across two real batches (61->68->74 documents) and its own next_move explicitly asks for more batches through the same reusable path, this time pre-checking for the HTML-entity defect it discovered (which caused 2/8 candidates, including a TJTO document, to be dropped last round). This round confirmed live that html.unescape() cleanly fixes that exact defect for the same TJTO document, making it recoverable, and found exactly 7 further tribunals with usable (Sentenca/Acordao, 4-17k char) candidates remaining in the sample pool. Continuing the same proven, low-risk mechanism is the best available advance toward RFC 0012's >=30/>=30 per-split floor -- no architectural change is justified until the corpus is materially bigger."
success_signal: "scripts/segmenter_governance_status.py run before and after the batch shows document_count strictly increasing above 74 and source.tribunal diversity growing beyond the 14 tribunals already in the store. uv run pytest -q and ruff check/format stay green with no changes needed to the ingestion script or its test suite (this batch exercises the existing mechanism plus a documented pre-decode step, not new production code). A PR is opened documenting the before/after governance numbers and merged."
status: "achieved"
---

# Goal: terceiro lote real multi-tribunal para #1050

Reusar `scripts/ingest_djen_sample_technique1_batch.py` sobre candidatos
reais de 7 tribunais ainda sem nenhum documento no store, aplicando
`html.unescape()` no `texto_limpo` de cada candidato antes de gerar
`candidates.json` (correcao para o achado de entidades HTML nao
decodificadas da rodada anterior), crescendo `document_count` e o teto de
val/test em direcao ao piso de RFC 0012 Sec 5 item 4.
