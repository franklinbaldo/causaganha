---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-4q9ktg-evidence-production-manifest-scale"
run_id: "2026-09-06-exciting-mccarthy-4q9ktg"
goal_id: "2026-09-06-exciting-mccarthy-4q9ktg-goal-cnj-lookup-bounded-scan"
kind: "runtime"
reference: "curl -sSL https://archive.org/download/tjro-juris/tjro-juris-manifest.csv (live production manifest, fetched this round)"
summary: "The live tjro-juris-manifest.csv has 1051 uploaded JURIS Parquet files (n_docs>0) spanning 327 distinct months from 1989-02 to 2026-07 — proving the unbounded CNJ-path scan in plan_decision_search/search_decisions is a present production issue, not a hypothetical future one."
---

# Evidência: escala real do manifesto JURIS em produção

```
curl -sSL "https://archive.org/download/tjro-juris/tjro-juris-manifest.csv" -o /tmp/manifest.csv
wc -l /tmp/manifest.csv          # 1052 (header + 1051 linhas)
awk -F, 'NR>1 && $3=="uploaded" && $4+0>0' /tmp/manifest.csv | wc -l     # 1051
awk -F, 'NR>1 && $3=="uploaded" && $4+0>0 {print $2}' /tmp/manifest.csv | sort -u | wc -l   # 327 meses distintos
awk -F, 'NR>1 && $3=="uploaded" && $4+0>0 {print $2}' /tmp/manifest.csv | sort | sed -n '1p;$p'   # 1989-02 ... 2026-07
```

Antes da correção, `plan_decision_search(..., consulta_por_cnj=True)` sem `data_inicio`/`data_fim` produz `plan.juris` com as 1051 entradas, e `search_decisions` monta `read_parquet([...1051 urls...])` via DuckDB httpfs para **toda** chamada de `decisoes_buscar(cnj=...)` — confirmado lendo `src/causaganha/decisoes/search.py:76` e `src/causaganha/decisoes/planner.py:112-120`.
