---
type: Pipeline
nome: tjro_juris
fonte: tjro_juris
pacote: tjro_juris
modo: batch
saida_canonica: internet_archive
mcp_status: tjro_juris_status
workflow: .github/workflows/tjro-sync.yml
cadencia_cron: "0 9 * * *"
tentativa_semantica: "início de um run schedule/workflow_dispatch do TJRO Sync"
sucesso_semantica: "run TJRO Sync concluído com conclusion=success; pode apenas confirmar que não havia janela nova"
publicacao_semantica: "manifest e parquets TJRO JURIS incorporados ao item autoritativo no Internet Archive"
canario_semantica: "provar artefato publicado; indisponibilidade live da fonte externa não deve virar false-red"
---

# Pipeline TJRO JURIS

Consome a fonte [TJRO JURIS](../sources/tjro-juris.md) e preserva o corpus de jurisprudência usado pelo produto e por experimentos derivados.

A cadência acima descreve oportunidade de execução, não um threshold de saúde. Tentativa, sucesso de execução e publicação são relógios distintos.
