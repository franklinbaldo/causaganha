---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-83kr8s-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-{0iuk22,c4y4rc,jyqinl,uyx7xc,mg2tp1,la7bsl}/run.md, scripts/segmenter_governance_status.py (live run), data/segmenter/documents/*.xml source_uri (live grep), data/segmenter_samples/*.jsonl (live scan), knowledge/backlog/issue-1050.md"
finding: "Live scripts/segmenter_governance_status.py confirms the previous round's (la7bsl) closing state exactly: document_count=93, val_ceiling_at_full_adjudication=14, test_ceiling_at_full_adjudication=14, corpus_scale_blocks_floor=true (still far below the >=30/>=30 RFC 0012 Sec 5 item 4 floor). A live grep of data/segmenter/documents/*.xml's source_uri attribute confirms 25 tribunals represented beyond TJRO's own 61 documents (TJMS x4, TRF4 x3, TJPA x3, TJPI x2, 21 further tribunals x1 each = 32 non-TJRO documents, matching 93-61=32 exactly) and lists the 32 djen_sample_technique1 candidate ids already ingested across batches 1-5. A fresh programmatic scan of data/segmenter_samples/*.jsonl for Sentenca/Acordao candidates 2500-18000 raw chars, excluding those 32 already-used ids, finds 258 unused in-range candidates, 161 of which parse cleanly as XML on their raw texto_limpo (ET.fromstring(f'<text>{texto}</text>')) with zero cleanup needed -- confirming la7bsl's finding that supply, not diversity, is now the only lever: no brand-new tribunal remains in the pool (only 'TJRO' and one malformed empty-tribunal record turn up outside the 25 already-represented tribunals). Selected 8 XML-clean, mid-length (3868-11350 char) Sentenca candidates spread across 8 already-represented tribunals with the deepest remaining pools (TRF5, TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES) for this round's batch, pre-checked for the two previously mapped preprocessing risks (HTML entities via `&[a-zA-Z]+;` regex, CRLF line endings) -- neither risk present in any of the 8 selected texts."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   `document_count=93`, `val_ceiling_at_full_adjudication=14`,
   `test_ceiling_at_full_adjudication=14`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (la7bsl) deixou.

2. **25 tribunais ja representados** (32 documentos nao-TJRO), confirmado
   por grep ao vivo em `data/segmenter/documents/*.xml`.

3. **258 candidatos nao usados no filtro 2500-18000 chars**, 161 deles
   ja XML-limpos sem qualquer limpeza de HTML necessaria. Nenhum
   tribunal novo restante -- diversidade esgotada, oferta em tribunais
   ja representados e o unico caminho de crescimento agora.

4. Selecionados para este lote: 8 candidatos Sentenca, um por tribunal
   entre os com maior oferta remanescente (TRF5, TJMT, TJRR, TJPA, TRF3,
   TJRJ, TJPB, TJES), todos XML-limpos e sem entidades HTML ou CRLF.
