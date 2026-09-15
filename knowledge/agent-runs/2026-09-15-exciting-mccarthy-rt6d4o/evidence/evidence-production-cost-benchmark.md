---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-rt6d4o-evidence-production-cost-benchmark"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
kind: "runtime"
reference: "scripts/benchmarks/djen_certification_probe.py; docs/planning/evidence/djen-certification-probe.json; arquivo real https://archive.org/download/djen-tjro-2026/comunicacoes.parquet"
summary: "Rodada ao vivo contra o Parquet de produção real (não certificado -- confirma o achado do audit de 11/09) medindo o custo extra do SELECT file_name,key,value FROM parquet_kv_metadata([...]) antes do lookup DJEN real (CNJ 70058285020258220014, 64 ocorrências, mesmo item usado pelo benchmark de ROW_GROUP_SIZE). Com conexão nova a cada chamada (cenário real de uma busca por sessão de navegador): custo marginal médio de -0.029s (dentro do ruído de rede de ~3-6s por chamada neste ambiente -- efetivamente imperceptível). Com conexão reutilizada e object_cache ligado (5 chamadas na mesma conexão): custo marginal médio de +0.629s por chamada -- parquet_kv_metadata parece não compartilhar o cache de metadados de read_parquet no mesmo arquivo/conexão. Como o fluxo real do site faz exatamente 1 checagem de certificação por busca por CNJ (não chamadas repetidas na mesma conexão), o cenário de conexão nova é o representativo do custo real; o de conexão reutilizada fica documentado para completude, não como o número operacional."
---

# Medição real do custo extra da inspeção do rodapé (#1469)

Evidência bruta em `docs/planning/evidence/djen-certification-probe.json` (6 séries de 5 chamadas cada, `lookup_only`/`footer_check_only`/`footer_check_then_lookup` × `object_cache` on/off). Reproduzível com `uv run python -m scripts.benchmarks.djen_certification_probe`.
