---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-96cgqx-evidence-batch13-red-test"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
goal_id: "2026-09-16-exciting-mccarthy-96cgqx-goal-djen-sample-batch13"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth"
summary: "RED confirmado antes da ingestao: `uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth -q` falha com `AssertionError: assert 121 >= 123` (document_count real ainda 121, hashes TJSE/TJRS ainda ausentes). Candidatos selecionados por scan ao vivo de data/segmenter_samples/*.jsonl (excluindo TJRO e arquivos auxiliares *_annotation_gold/*_annotation_raw, filtro 2500-18000 chars, Sentenca/Acordao, deduplicado contra source_uri e source_hash do store real): TJSE/578949084 (Acordao, unico candidato elegivel restante para TJSE) e TJRS/458637070 (Sentenca, unico candidato elegivel restante para TJRS), ambos em tribunais no menor store_count nao-singleton (2 cada, empatados com TJPI/TJMG/TRF5/TRF2/TJTO). TJSE tinha 3 caracteres de controle ASCII (U+001C/U+001D como aspas improvisadas, U+0013 como parentese de abertura) -- substituicao preservando o comprimento (classe de risco 7). TJRS tinha markup HTML bruto embutido (<b>/<table>/<tr>/<td>) -- limpo com o cleaner do lote 3 (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py)."
---

# Evidencia: RED test batch13

Comando: `uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch13_corpus_growth -q`

Resultado: FAILED -- `AssertionError: assert 121 >= 123` (1 failed).

`docs/planning/evidence/segmenter-djen-sample-batch13-candidates.json`
contem os dois candidatos com `texto_limpo` ja pre-processado (TJSE com
substituicao de caracteres de controle, TJRS com HTML limpo). Hashes de
conteudo calculados com `segmenter_dataset.dedup.content_hash`:
TJSE=`c002c5d5...`, TJRS=`eed26aff...` -- nenhum presente no store atual
(verificado contra o conjunto `{doc.source.source_hash for doc in
store.list_documents()}`).
