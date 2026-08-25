---
type: Pipeline
nome: djen
fonte: djen
pacote: djen_backup
modo: batch
saida_canonica: internet_archive
mcp_status: djen_backup_status
workflow: .github/workflows/collect-zips.yml
cadencia_cron: "*/20 * * * *"
tentativa_semantica: "início de um run schedule/workflow_dispatch do Collect ZIPs"
sucesso_semantica: "run Collect ZIPs concluído com conclusion=success; não implica publicação de novos ZIPs"
publicacao_semantica: "estado DJEN incorporado à autoridade publicada no Internet Archive (parquet + manifest-log)"
canario_semantica: "canário E2E publicado existente; manter como prova DJEN/deploy"
---

# Pipeline DJEN

Consome a fonte [DJEN](../sources/djen.md), preserva os artefatos e alimenta a camada consolidada usada pelo produto.

A cadência acima descreve oportunidade de execução, não um threshold de saúde. Tentativa, sucesso de execução e publicação são relógios distintos.
