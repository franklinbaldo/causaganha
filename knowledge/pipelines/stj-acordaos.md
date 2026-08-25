---
type: Pipeline
nome: stj_acordaos
fonte: stj_acordaos
pacote: stj_acordaos
modo: batch
saida_canonica: internet_archive
mcp_status: stj_acordaos_status
workflow: .github/workflows/stj-sync.yml
cadencia_cron: "0 7 * * *"
tentativa_semantica: "início de um run schedule/workflow_dispatch do STJ Sync"
sucesso_semantica: "run STJ Sync concluído com conclusion=success; não implica que houve acórdão novo"
publicacao_semantica: "manifest e recursos STJ incorporados ao item autoritativo no Internet Archive"
canario_semantica: "provar reachability/estrutura do artefato publicado; WAF da fonte não é requisito de saúde live"
---

# Pipeline STJ

Consome a fonte [STJ acórdãos](../sources/stj-acordaos.md) e disponibiliza seus registros para reconciliação e consulta processual.

A cadência acima descreve oportunidade de execução, não um threshold de saúde. Tentativa, sucesso de execução e publicação são relógios distintos.
