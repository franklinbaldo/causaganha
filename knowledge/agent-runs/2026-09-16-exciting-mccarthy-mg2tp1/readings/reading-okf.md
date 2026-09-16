---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-mg2tp1-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-uyx7xc/run.md, knowledge/backlog/issue-1050.md, scripts/ingest_djen_sample_technique1_batch.py, scripts/segmenter_governance_status.py (live run), data/segmenter_samples/*.jsonl (live scan), data/segmenter/documents/*.xml (live scan)"
finding: "Live scripts/segmenter_governance_status.py confirms the previous round's closing state exactly: document_count=81, val_ceiling_at_full_adjudication=12, test_ceiling_at_full_adjudication=12, corpus_scale_blocks_floor=true. A live scan of data/segmenter/documents/*.xml's source tribunal attribute (via grep, not the broken naive XML-attribute-position parse tried first) confirms 21 tribunals represented (TJRO plus the 20 from batch1+batch2+batch3), matching the previous round exactly. A fresh scan of data/segmenter_samples/*.jsonl (excluding *_annotation_raw/_gold.jsonl) for Sentenca/Acordao candidates 4000-17000 raw chars long in tribunals NOT yet represented -- correcting the previous round's field names (candidate objects use top-level `text` + `info.tribunal`/`info.tipoDocumento`/`info.id`, not `texto_limpo`/`tribunal` at top level, and per-tribunal identity must be derived from the sample filename since `info.tribunal` is often an empty string) -- finds real, usable candidates in exactly 3 tribunals not yet represented: TJSC (1 candidate), TRF4 (3 candidates), TRF6 (1 candidate). The 9 tribunals the previous round found unusable (TJAC, TJAM, TJAP, TJMS, TJPE, TJSP, TRF1, STM, plus TRF6 itself which only had a sub-4000-char candidate then) were rechecked and remain unusable under the same length/type filter -- unchanged. All 5 selected candidates' raw texto_limpo fails ET.fromstring(f'<text>{texto}</text>') with a 'mismatched tag' error at the same position (an unclosed <meta> inside an <html><head>...<body> wrapper, the exact defect class the previous round's docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py was built for) -- reusing that cleaner unmodified on all 5 candidates produces XML-parseable, HTML-entity-free plain text (0 residual '&[a-zA-Z]+;' occurrences in every candidate, confirmed live) ranging 2451-3977 chars, comparable to the shortest djen_sample_technique1 documents already in the store (2104-2161 chars)."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   `document_count=81`, `val_ceiling_at_full_adjudication=12`,
   `test_ceiling_at_full_adjudication=12`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (uyx7xc) deixou.

2. **21 tribunais ja representados** (TJRO + 20 de batch1/2/3), confirmado
   por scan ao vivo de `data/segmenter/documents/*.xml`.

3. **Apenas 3 tribunais novos com candidatos usaveis restam** no pool de
   amostras (TJSC com 1 candidato, TRF4 com 3, TRF6 com 1) -- os demais 9
   tribunais ja mapeados pela rodada anterior como sem candidato usavel
   continuam sem candidato usavel.

4. **Mesmo defeito de markup HTML bruto da rodada anterior**: os 5
   candidatos selecionados falham `ET.fromstring` no texto bruto (wrapper
   `<html><head><meta>...<body>` sem fechamento), reproduzido pelo mesmo
   limpador `docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`
   sem nenhuma alteracao, produzindo texto XML-parseavel e sem entidades
   HTML residuais (0 ocorrencias de `&[a-zA-Z]+;`) para todos os 5,
   comparavel em tamanho aos documentos mais curtos ja no store.
