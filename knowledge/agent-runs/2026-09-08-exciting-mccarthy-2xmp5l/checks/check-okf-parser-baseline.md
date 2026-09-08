---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-2xmp5l-check-okf-parser-baseline"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
command: "UV_HTTP_TIMEOUT=180 uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "observed"
summary: "First invocation this round required a full `uv sync` (this environment had no cached venv/downloads for causaganha's Python deps), which hit a transient network timeout on beartype==0.22.9 under the default 30s UV_HTTP_TIMEOUT and had to be retried with UV_HTTP_TIMEOUT=180. Once dependencies resolved, the check itself ran and correctly flagged this round's own scaffolded run.md as non-conformant (OKF022: AgentReading.run_id referencing an AgentRun id that didn't exist yet, because run.md's own `id` field was still the scaffold's empty string) — exactly the expected gap-driven signal the scaffold's own instructions describe. Fixed by filling in run.md's id/started_at/branch_at_start/commit_at_start and the four reading_id fields to match the actual reading files already written."
---

# Check: okf-parser baseline (após scaffold + leituras)

Primeira invocação exigiu `uv sync` completo (sem cache neste ambiente), com um timeout de rede transitório em `beartype` contornado com `UV_HTTP_TIMEOUT=180`. O check em si apontou corretamente a lacuna esperada: `run.md` ainda tinha `id: ""` do scaffold, quebrando a FK das quatro leituras já escritas. Corrigido preenchendo `run.md` com o id real e os IDs de leitura.
