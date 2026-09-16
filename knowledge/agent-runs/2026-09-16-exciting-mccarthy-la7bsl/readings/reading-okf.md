---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-la7bsl-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-{0iuk22,c4y4rc,jyqinl,mg2tp1,uyx7xc}/run.md, scripts/segmenter_governance_status.py (live run), data/segmenter/documents/*.xml (live grep), data/segmenter_samples/*.jsonl (live scan), docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json"
finding: "Live scripts/segmenter_governance_status.py confirms the previous round's closing state exactly: document_count=86, val_ceiling_at_full_adjudication=13, test_ceiling_at_full_adjudication=13, corpus_scale_blocks_floor=true (still far below the >=30/>=30 RFC 0012 Sec 5 item 4 floor). A live grep of data/segmenter/documents/*.xml's source_uri attribute confirms 24 tribunals represented (TJRO x61, TRF4 x3, plus 22 other tribunals x1 each) and 25 distinct djen_sample_technique1 document ids already ingested across batches 1-4. A fresh scan of data/segmenter_samples/*.jsonl for Sentenca/Acordao candidates 2500-18000 raw chars, excluding those 25 already-used ids, widened per mg2tp1's own next_move to include already-represented tribunals (not just new ones), finds 261 unused, in-range candidates -- an order of magnitude more supply than any single round can process, confirming corpus growth is now supply-unconstrained. Critically, this wider length filter (2500 chars, vs. the 4000-char floor prior rounds used) surfaces 4 usable Acordao candidates in TJMS -- a genuinely new, 25th tribunal that all five same-day prior rounds' 4000-char filter had missed and mg2tp1 explicitly listed as 'unusable'. All 4 TJMS candidates (32000358, 32009610, 32021195, 32021228) plus 3 more selected in already-represented tribunals (TJPA x2: 581167448, 581175574; TJPI x1: 22443805) pass ET.fromstring(f'<text>{texto}</text>') on their raw texto_limpo with zero cleanup needed -- unlike batches 3/4, none of this batch's 7 candidates carry the unclosed-HTML-wrapper defect those batches' cleaner was built for."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   `document_count=86`, `val_ceiling_at_full_adjudication=13`,
   `test_ceiling_at_full_adjudication=13`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (mg2tp1) deixou.

2. **24 tribunais ja representados**, 25 ids `djen_sample_technique1` ja
   ingeridos via batches 1-4 (confirmado por grep ao vivo em
   `data/segmenter/documents/*.xml`).

3. **261 candidatos nao usados no filtro ampliado** (2500-18000 chars,
   Sentenca/Acordao, tribunais ja representados incluidos) -- oferta deixa
   de ser o gargalo.

4. **TJMS e um 25o tribunal novo, ate agora invisivel**: o filtro de 4000
   chars usado pelas 5 rodadas anteriores do mesmo dia escondia 4
   candidatos Acordao TJMS (2516-2980 chars) que passam limpos por
   `ET.fromstring` sem nenhuma limpeza de HTML.

5. Selecionados para este lote: 4 TJMS + 2 TJPA + 1 TJPI, todos
   XML-parseaveis no texto bruto -- nenhum precisa do limpador HTML das
   rodadas batch3/4.
