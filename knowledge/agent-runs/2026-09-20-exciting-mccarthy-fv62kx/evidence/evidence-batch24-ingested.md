---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-batch24-ingested"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
kind: "runtime"
reference: "commit dc71766 on claude/exciting-mccarthy-fv62kx; scripts/segmenter_governance_status.py; uv run pytest -q tests/segmenter_dataset"
summary: "6 novos documentos reais ingeridos via scripts/ingest_djen_sample_technique1_batch.py (TJBA/574460088, TJMA/42725100, TJPI/22443826, TJES/577051509, TJGO/543517919, TJPB/578906897). document_count 179->185, annotation_count 232->238, teto de val/test 27/27->28/28, confirmados ao vivo antes e depois via scripts/segmenter_governance_status.py. git status --short data/segmenter confirmou exatamente 6 novos documents/*.xml e 6 novos annotations/<id>/. uv run pytest -q tests/segmenter_dataset: 208 passed (100% verde) apos a ingestao. uv run ruff check/format --check limpos. scripts/segmenter_semantic_audit.py: zero achados novos entre os 6 documentos (0 doc_id novo entre os 11 achados pre-existentes)."
---

# Evidência: batch24 ingerido e verificado

- **Antes**: `document_count=179`, `val_ceiling=test_ceiling=27` (confirmado ao vivo no início da rodada).
- **Depois**: `document_count=185`, `annotation_count=238`, `val_ceiling=test_ceiling=28` (confirmado ao vivo após a ingestão, `scripts/segmenter_governance_status.py`).
- **Fidelidade verbatim**: verificação independente via `segmenter_dataset.store._text_element_to_labels` (não o autorrelato dos subagentes) confirmou reconstrução byte-a-byte idêntica ao `texto_limpo` de origem para os 6 documentos, antes da ingestão real.
- **git status**: exatamente 6 `documents/*.xml` e 6 `annotations/<id>/` novos (`git status --short data/segmenter`), sem write no-op silencioso.
- **Testes**: `uv run pytest -q tests/segmenter_dataset` → `........................................................................ [ 18%] ... [100%]`, 208 passed, 0 failed.
- **Lint**: `uv run ruff check` → "All checks passed!"; `uv run ruff format --check` → "454 files already formatted".
- **Auditoria semântica**: `scripts/segmenter_semantic_audit.py` reportou 11 achados, todos em `doc_id`s pré-existentes do corpus — nenhum dos 6 `doc_id`s novos deste lote aparece na lista (verificado programaticamente).
- **Commit**: `dc71766` em `claude/exciting-mccarthy-fv62kx`, pushed para `origin`.
