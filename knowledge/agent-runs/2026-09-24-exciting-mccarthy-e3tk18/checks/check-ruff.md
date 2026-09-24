---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-e3tk18-check-ruff"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal_id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
summary: "'All checks passed!' e '455 files already formatted' (apos ruff format reformatar o novo bloco de testes uma vez, antes de reverificar --check)."
---

# Check: ruff sobre o repositorio inteiro

Rodado apos escrever os 5 novos testes e a correcao do regex, para
confirmar que nenhum arquivo tocado nesta rodada quebra o
lint/format estrito do projeto.
