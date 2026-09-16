---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-jyqinl-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-0iuk22/run.md, knowledge/backlog/issue-1050.md, scripts/ingest_djen_sample_technique1_batch.py, scripts/segmenter_governance_status.py (live run), data/segmenter_samples/*.jsonl (live scan)"
finding: "Live run of scripts/segmenter_governance_status.py confirms the previous round's closing state exactly: document_count=68, val_ceiling_at_full_adjudication=10, test_ceiling_at_full_adjudication=10, corpus_scale_blocks_floor=true. store.list_documents() confirms source.tribunal is {TJRO:61, TJMT:1, TJCE:1, TJES:1, TRF3:1, TRF5:1, TJSE:1, TJPA:1} -- exactly the 7 non-TJRO tribunals the previous round (0iuk22) added, none since. A fresh scan of data/segmenter_samples/*.jsonl (excluding *_annotation_raw/_gold.jsonl, which are a different, already-labeled schema not meant for fresh Technique-1 annotation) for tribunals NOT yet in the store and tipoDocumento in {Sentença, Acórdão} (the only two the current guideline supports) finds real, unused, high-cue-score candidates in at least 18 further tribunals never touched (TJAC, TJBA, TJGO, TJMA, TJMG, TJMS, TJPB, TJPI, TJRJ, TJRN, TJRR, TJRS, TJSP, TJTO, TRF2, TRF6, STM, TST), each with 2-40 candidates. This confirms the previous round's next_move is still exactly right and still unstarted: the ingestion mechanism (scripts/ingest_djen_sample_technique1_batch.py) and its test suite are unchanged and reusable as-is; only a second real batch (new candidates, new Technique 1 annotations) is missing. Selected 8 top-cue-score Sentença candidates, one per new tribunal (TJBA, TJGO, TJMA, TJPB, TJRJ, TJRN, TJRR, TJTO), each already flagged for a rare category (preliminar/honorarios/custas/relatorio/ementa/acordao_decisorio) and within a manageable 5-16k character range for verbatim Technique 1 annotation."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   confirma `document_count=68`, `val_ceiling_at_full_adjudication=10`,
   `test_ceiling_at_full_adjudication=10`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (0iuk22) deixou, sem regressao.

2. **Apenas 7 tribunais alem de TJRO ja usados** (TJMT, TJCE, TJES, TRF3,
   TRF5, TJSE, TJPA -- um documento cada, do lote 1). Nenhum lote novo foi
   feito desde entao.

3. **Escaneei `data/segmenter_samples/*.jsonl` ao vivo** (excluindo os
   arquivos `*_annotation_raw/_gold.jsonl`, que sao um schema diferente,
   ja rotulado) e confirmei candidatos reais, nao usados, com bom
   `cue_score`, em pelo menos 18 tribunais ainda sem nenhum documento no
   store: TJAC, TJBA, TJGO, TJMA, TJMG, TJMS, TJPB, TJPI, TJRJ, TJRN,
   TJRR, TJRS, TJSP, TJTO, TRF2, TRF6, STM, TST.

4. **Selecao para este lote**: 8 candidatos `Sentença` de 8 tribunais
   novos (TJBA, TJGO, TJMA, TJPB, TJRJ, TJRN, TJRR, TJTO), cada um com
   `cue_score>=6` (categorias raras: preliminar/honorarios/custas/
   relatorio/ementa/acordao_decisorio) e tamanho manejavel (5-16k
   caracteres) para anotacao Technique 1 verbatim por subagente.

5. **Mecanismo de ingestao** (`scripts/ingest_djen_sample_technique1_batch.py`,
   `scripts/annotate_second_independent.py`'s override contract) permanece
   inalterado e reusavel como esta -- nao ha necessidade de mudar codigo de
   producao para este lote, apenas rodar o mecanismo ja provado sobre
   candidatos novos.
