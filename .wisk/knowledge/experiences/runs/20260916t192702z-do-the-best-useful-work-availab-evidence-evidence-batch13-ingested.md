---
type: "RunEvidence"
id: "run-evidence/20260916t192702z-do-the-best-useful-work-availab/evidence-batch13-ingested"
run: "runs/20260916T192702Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "docs/planning/evidence/segmenter-djen-sample-batch13-candidates.json"
summary: "scripts/ingest_djen_sample_technique1_batch.py ingeriu 5 documentos reais (TST/237077355, TJPI/22443810, TJRS/458637070, TJSE/578949084, TRF5/349055692) no store data/segmenter apos 6 anotacoes Tecnica 1 via subagents independentes. document_count subiu 121->126 (scripts/segmenter_governance_status.py, ao vivo), val/test ceiling 18->19. Um sexto candidato (TJSC/587254906) foi anotado e ingerido, depois revertido: ja existia no store desde o lote 4 (PR #1545) -- o campo info.tribunal do jsonl de origem (tjsc_acordao.jsonl) esta em branco para todos os registros, quebrando silenciosamente o dedup por (tribunal, id_documento) contra o store real. A anotacao redundante foi apagada (mesmo annotator_config da preexistente, sem valor de segunda anotacao independente). Quatro overrides --allowed-unmatched-overrides foram necessarios, todos verificados contra o texto-fonte bruto. Dois candidatos precisaram do limpador HTML->texto do lote 3 (TJSC antes de reverter, TJRS, TST) por markup bruto na fonte; dois tiveram NBSP mid-documento corrigido por reanotacao; um (TJSE) teve caracteres de controle ASCII (aspas improvisadas) substituidos por aspas comuns antes da anotacao. Novo teste de regressao test_real_store_reflects_batch13_corpus_growth (tests/segmenter_dataset/test_segmenter_governance_status.py) trava o crescimento. knowledge/backlog/issue-1050.md atualizado com o lote 13 e a nova classe de risco 11 (tribunal em branco no jsonl quebra dedup)."
goal: "run-goals/20260916t192702z-do-the-best-useful-work-availab/goal-segmenter-batch13"
---

# RunEvidence
