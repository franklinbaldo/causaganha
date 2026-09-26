---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-fipj1n-check-okf-parser-after-readings-goal-decisions"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado após preencher run.md (id/leituras/goal/decisões/evidence RED+GREEN/check-ruff) e antes do check final. conformant=true, 0 diagnostics, concept_count=2374, markdown_count=2377. A execução baseline no início da rodada (antes de criar o run.md) também era conformant=true/0 diagnostics; a execução intermediária, feita antes de preencher o id do run.md, mostrou corretamente 4 erros OKF022 (AgentReading sem AgentRun correspondente) — confirmando que o gate reage ao estado real do relatório, não é um check estático."
---

# Check: okf-parser (após leituras, goal, decisões, evidência RED/GREEN)

`uv run okf-parser check knowledge --relational-schema okf.schema.sql`
retornou `conformant: true`, 0 diagnostics, após o `run.md` ser preenchido
com `id` e as referências de leitura. Uma execução intermediária, feita
enquanto `run.md` ainda tinha `id: ""`, corretamente reportou 4 erros
`OKF022` (chave estrangeira órfã) para as 4 leituras já escritas —
confirmando que o relatório está de fato guiando a rodada, não sendo
preenchido em paralelo sem relação com o estado real do bundle.
