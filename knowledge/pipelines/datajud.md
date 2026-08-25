---
type: Pipeline
nome: datajud
fonte: datajud
pacote: datajud
modo: live_e_batch
saida_canonica: cache_e_indice
mcp_status: datajud_status
workflow: .github/workflows/datajud-enrich.yml
cadencia_cron: "13 5 * * *"
tentativa_semantica: "início de um run schedule/workflow_dispatch do DataJud Enrich"
sucesso_semantica: "run DataJud Enrich concluído com conclusion=success; mede processamento, não existência de nova geração"
publicacao_semantica: "bundle datajud-state-{tribunal}.zip publicado e coerente no Internet Archive"
canario_semantica: "prova mínima publicada + consulta pública barata; ainda a materializar em #892"
---

# Pipeline DataJud

Consome a fonte [DataJud](../sources/datajud.md) para enriquecimento processual e consultas ao vivo de facetas.

A cadência acima descreve oportunidade de execução, não um threshold de saúde. Tentativa, sucesso de execução e publicação são relógios distintos.
