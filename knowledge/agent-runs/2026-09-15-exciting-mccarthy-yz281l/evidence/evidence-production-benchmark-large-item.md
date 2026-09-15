---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-yz281l-evidence-production-benchmark-large-item"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
goal_id: "2026-09-15-exciting-mccarthy-yz281l-goal-row-group-size-a1b"
kind: "runtime"
reference: "docs/planning/evidence/row-group-size-a1b-production.json"
summary: "scripts/benchmarks/row_group_size_production.py rodado ao vivo contra djen-tjro-2026/comunicacoes.parquet (baixado de archive.org, 1.041.723 linhas reais, item grande de referência do epic #1468/#1470/#1471). Para os 4 ROW_GROUP_SIZE candidatos (16384/32768/65536/122880-default), reescrito sob ORDER BY numero_processo, data_disponibilizacao, id (o contrato real de exporter.py): o point-lookup pelo CNJ mais repetido do arquivo (70058285020258220014, 64 ocorrências) tocou exatamente 1 row group em TODOS os tamanhos -- nenhum ganho de pruning ao encolher. Já a consulta de 1 dia (2026-09-01) tocou 9 row groups no default e até 64 no menor tamanho testado -- regressão real e mensurável. Tamanho de arquivo e compressão também pioram ligeiramente com row groups menores (81.57MB/26.7% no default vs 82.52MB/26.5% em 16384)."
---

# Evidência: benchmark ROW_GROUP_SIZE contra item grande real

Arquivo de evidência: `docs/planning/evidence/row-group-size-a1b-production.json`. Confirma, com dado real (não sintético), que o item grande do epic #1468 não se beneficia de um `ROW_GROUP_SIZE` menor que o default do DuckDB.
