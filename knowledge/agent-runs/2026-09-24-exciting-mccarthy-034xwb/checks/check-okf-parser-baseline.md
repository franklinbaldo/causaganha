---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-034xwb-check-okf-parser-baseline"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
evidence_id: null
---

# Check: okf-parser baseline (scaffold copiado)

Rodado logo apos copiar o scaffold para `run.md` desta rodada (ainda
em rascunho: `completed_at`/`primary_goal_id`/etc vazios). Resultado:
`conformant: true`, `concept_count: 2101`, `diagnostics: []`. O
proprio scaffold avisa que 3 testes pytest falham enquanto o relatorio
esta em rascunho (nao o `okf-parser check` em si) -- confirmado
consistente com essa nota.
