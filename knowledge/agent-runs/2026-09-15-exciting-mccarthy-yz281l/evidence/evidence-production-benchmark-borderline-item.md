---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-yz281l-evidence-production-benchmark-borderline-item"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
goal_id: "2026-09-15-exciting-mccarthy-yz281l-goal-row-group-size-a1b"
kind: "runtime"
reference: "docs/planning/evidence/row-group-size-a1b-production-borderline-item.json"
summary: "O plano de otimização (docs/planning/parquet-storage-optimization-plan.md, secao 1b) exige medir tambem a classe 'item pequeno' (um so row group no default) -- o exemplo original do plano (djen-tjro-2025) mostrou-se desatualizado (checado ao vivo: 1.634.023 linhas, 14 row groups hoje, ja nao e um item de 1 grupo). Substitui por djen-2025-12-23/comunicacoes.parquet, real, 95.783 linhas, exatamente 1 row group no default -- o cenario de fronteira que a secao pede. Mesmo resultado do item grande: o CNJ mais repetido (00662078620258160000, 1691 ocorrencias) toca 1 row group em todos os 4 tamanhos testados, inclusive nos que quebram o arquivo em ate 6 grupos (16384). Tamanho de arquivo cresce levemente com row groups menores (7.69MB vs 7.665MB no default)."
---

# Evidência: benchmark ROW_GROUP_SIZE contra item de fronteira real

Arquivo de evidência: `docs/planning/evidence/row-group-size-a1b-production-borderline-item.json`. Fecha a segunda classe de item que o plano exigia medir (pequeno/fronteira), usando um item real já que o exemplo original do plano (djen-tjro-2025) não é mais representativo dessa classe (cresceu para 14 row groups desde que o plano foi escrito).
