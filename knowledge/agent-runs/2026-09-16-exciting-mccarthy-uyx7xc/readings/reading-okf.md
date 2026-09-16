---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-uyx7xc-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-jyqinl/run.md, knowledge/backlog/issue-1050.md, scripts/ingest_djen_sample_technique1_batch.py, scripts/segmenter_governance_status.py (live run), data/segmenter_samples/*.jsonl (live scan), data/segmenter/documents/*.xml (live scan)"
finding: "Live scripts/segmenter_governance_status.py confirms the previous round's closing state exactly: document_count=74, val_ceiling_at_full_adjudication=11, test_ceiling_at_full_adjudication=11, corpus_scale_blocks_floor=true. A live scan of data/segmenter/documents/*.xml's tribunal attribute confirms 14 tribunals represented (TJRO + TJBA, TJCE, TJES, TJMA, TJMT, TJPA, TJPB, TJRJ, TJRN, TJRR, TJSE, TRF3, TRF5), matching batch1+batch2 exactly. A fresh scan of data/segmenter_samples/*.jsonl (excluding *_annotation_raw/_gold.jsonl) for Sentenca/Acordao candidates 4000-17000 chars long in tribunals NOT yet represented finds real, usable candidates in only 7 tribunals now: TJGO, TJMG, TJPI, TJRS, TJTO, TRF2, TST -- the remaining unrepresented tribunals in the sample pool (TJAC, TJAM, TJAP, TJMS, TJPE, TJSP, TRF1, TRF6, STM) only have 'Decisão'-type or very short candidates, which the current v7.1 guideline's document_type_hint does not cover (scripts/ingest_djen_sample_technique1_batch.py's _DOCUMENT_TYPE_MAP only maps Sentença/Acórdão), so they are correctly left out rather than guessed at. Applying html.unescape() to each of the 7 selected candidates' texto_limpo removes 100% of the '&[a-zA-Z]+;' occurrences found (394 in the TJGO pick, 321 in TJMG, 118 in TJRS, 513 in TJTO -- notably the same TJTO document id (285645419) batch2 discovered and dropped, now recoverable) and 0 remain in any candidate after decoding, confirming the previous round's proposed fix (pre-decode with html.unescape) works cleanly for this exact defect class before spending a subagent redo cycle discovering it live again."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   `document_count=74`, `val_ceiling_at_full_adjudication=11`,
   `test_ceiling_at_full_adjudication=11`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (jyqinl) deixou.

2. **14 tribunais ja representados** (TJRO + 13 de batch1/batch2),
   confirmado por scan ao vivo de `data/segmenter/documents/*.xml`.

3. **Apenas 7 tribunais novos com candidatos usaveis restam** no pool de
   amostras (TJGO, TJMG, TJPI, TJRS, TJTO, TRF2, TST) -- os demais
   tribunais ainda nao usados so tem candidatos `Decisão` (tipo nao
   coberto pela guideline v7.1) ou texto curto demais.

4. **Correcao do achado da rodada anterior testada ao vivo**: aplicar
   `html.unescape()` no `texto_limpo` de cada candidato remove 100% das
   entidades HTML literais encontradas (ate 513 ocorrencias num
   candidato), incluindo o mesmo documento TJTO (id=285645419) descartado
   na rodada anterior -- agora recuperavel sem mudar o mecanismo de
   ingestao, so o pre-processamento do `candidates.json`.
