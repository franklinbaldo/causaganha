---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5crg57-check-full-suite-final"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
command: "uv run pytest -q (repositório inteiro, com run.md já completo)"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-5crg57-evidence-green-test"
summary: "Suíte completa 100% verde (nenhuma falha, 1 skip pré-existente não relacionado) após completed_at/result_summary/next_move do run.md serem preenchidos -- confirma que a cascata de 3 falhas prevista pelo próprio scaffold enquanto o relatório está em rascunho não sobrevive à finalização do relatório. uv run ruff check . e ruff format --check . limpos no repositório inteiro."
---

# Check: suíte completa final

Rodado imediatamente após completar `run.md` e regenerar (sem diff) os arquivos derivados de OKF (`web/src/lib/processoConsultar.gen.ts`, `src/causaganha_mcp/_generated/domain_models.py`) -- a forma inferida pelo `okf-parser` não mudou o suficiente para exigir regeneração real desta vez.
