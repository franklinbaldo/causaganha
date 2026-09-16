---
type: "RunEvidence"
id: "run-evidence/20260916t162542z-do-the-best-useful-work-availab/evidence-batch11-ingested"
run: "runs/20260916T162542Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "docs/planning/evidence/segmenter-djen-sample-batch11-2026-09-16.json"
summary: "scripts/ingest_djen_sample_technique1_batch.py ingeriu 2 documentos reais (TJRN/72796443, TJMA/42728353) no store data/segmenter apos duas anotacoes Tecnica 1 independentes via subagents. document_count subiu 117->119 (scripts/segmenter_governance_status.py, ao vivo). Um defeito de processo foi pego e revertido antes do primeiro git add: a primeira tentativa de ingestao usou o mesmo diretorio para o texto-fonte bruto e a saida tagueada do subagente (nomeada <id>.tagged.txt), e o glob('*.txt') do script casou o arquivo errado (o texto-fonte sem tags) para o TJRN, produzindo uma anotacao com covered_categories mas zero labels -- corrigido usando um diretorio de saida separado, documentado como classe de risco 10 em knowledge/backlog/issue-1050.md."
goal: "run-goals/20260916t162542z-do-the-best-useful-work-availab/goal-segmenter-batch11"
---

# RunEvidence
