---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-0iuk22-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-16-exciting-mccarthy-c4y4rc/run.md, knowledge/backlog/issue-1050.md, docs/rfc/0012-segmenter-dataset-confiavel-baseline.md, src/segmenter_dataset/splits.py, src/segmenter_dataset/candidate_mining.py, scripts/ingest_juris_technique1_batch.py, scripts/segmenter_governance_status.py (live run), data/segmenter_samples/*.jsonl"
finding: "Live run of scripts/segmenter_governance_status.py confirms the previous round's closing state: document_count=61 (all TJRO), val_ceiling_at_full_adjudication=9, test_ceiling_at_full_adjudication=9, corpus_scale_blocks_floor=true. The mechanism to raise that ceiling is genuinely unbuilt for non-TJRO sources: scripts/ingest_juris_technique1_batch.py (the only script that mints brand-new DocumentRecords with a first Technique-1 annotation) is hardcoded to TJRO JURIS candidates (SOURCE_SYSTEM='tjro_juris', tribunal='TJRO', and a candidate JSON shape specific to the JURIS-pool research step: id_documento/nr_processo/tipo/classe/orgao/texto_limpo). Meanwhile data/segmenter_samples/*.jsonl already holds ~830 REAL, already-fetched full judicial texts from ~30 different tribunals (TJAC, TJAM, TJBA, TJCE, TJES, TJGO, TJMA, TJMG, TJMT, TJPA, TJPB, TJPE, TJPI, TJRJ, TJRN, TJRR, TJRS, TJSE, TJSP, TJTO, TRF1-6, STM, ...), each already carrying a document.info (id/tribunal/tipoDocumento/nomeOrgao/nomeClasse/source_item/source_zip/source_json/sha256) and pre-computed cue_hits/cue_score from a heuristic identical in spirit to src/segmenter_dataset/candidate_mining.py -- entirely unused by the store (none of these documents have ever been ingested). This is exactly the untapped 'mine real candidate documents... multiple tribunals' work item #1050 asks for, and closes the gap between the two: I need a generalized ingestion script (parallel to ingest_juris_technique1_batch.py but reading the segmenter_samples schema and deriving tribunal/document_type from candidate.info instead of hardcoding TJRO) plus real Technique-1 annotations for a first batch, using the canonical prompt at data/segmenter_splits/technique1_annotation_prompt.md."
---

# Leitura: conhecimento OKF relevante

1. **Estado real do store** (`uv run python scripts/segmenter_governance_status.py`):
   confirma `document_count=61`, `val_ceiling_at_full_adjudication=9`,
   `test_ceiling_at_full_adjudication=9`, `corpus_scale_blocks_floor=true`
   -- exatamente onde a rodada anterior (c4y4rc) deixou, sem regressao.

2. **Todos os 61 documentos sao TJRO** (`source.system` em
   `{tjro_juris: 54, internet_archive_djen_ocr: 7}`). Nenhum script de
   ingestao existente cobre outra fonte/tribunal:
   `scripts/ingest_juris_technique1_batch.py` (o unico que cria
   `DocumentRecord`s novos com uma primeira anotacao Technique 1) esta
   hardcoded para candidatos JURIS-TJRO (`SOURCE_SYSTEM = "tjro_juris"`,
   `tribunal="TJRO"`, schema de candidato especifico:
   `id_documento`/`nr_processo`/`tipo`/`classe`/`orgao`/`texto_limpo`).

3. **`data/segmenter_samples/*.jsonl` ja contem ~830 documentos judiciais
   reais, ja coletados, de ~30 tribunais diferentes** (TJAC, TJAM, TJBA,
   TJCE, TJES, TJGO, TJMA, TJMG, TJMT, TJPA, TJPB, TJPE, TJPI, TJRJ, TJRN,
   TJRR, TJRS, TJSE, TJSP, TJTO, TRF1-6, STM...), cada um com `info`
   (id/tribunal/tipoDocumento/nomeOrgao/nomeClasse/source_item/source_zip/
   source_json/sha256) e `cue_hits`/`cue_score` ja calculados por uma
   heuristica irma de `src/segmenter_dataset/candidate_mining.py` --
   **nunca ingeridos no store**. E exatamente o item de trabalho aberto de
   #1050 ("mine real candidate documents... multiple tribunals/sources"),
   ja pre-minerado e parado, faltando so o pipeline de ingestao +
   anotacao real.

4. **Prompt canonico Technique 1** (`data/segmenter_splits/technique1_annotation_prompt.md`):
   existe e documenta por que improvisar o prompt por lote causou 45% de
   falha no batch1 -- usar verbatim, um subagente por documento, com os
   dois checkpoints (listar categorias esperadas antes de marcar, verificar
   o rascunho depois).

5. **Lacuna concreta desta rodada**: falta um script de ingestao
   generalizado (paralelo a `ingest_juris_technique1_batch.py`, mas lendo
   o schema de `segmenter_samples` e derivando tribunal/tipo de documento
   de `candidate.info` em vez de fixar TJRO) mais anotacoes Technique 1
   reais para um primeiro lote, usando o prompt canonico acima.
