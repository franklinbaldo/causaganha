---
type: AgentReading
id: "2026-09-10-exciting-mccarthy-r3erpr-reading-claude-md"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start via the system-provided project instructions. Correctness rules unchanged from the last several rounds' reads: djen_raw is the transport code (never a verdict), 403 must never be treated as absent, genuine absent is 404/400/200-with-'Sem comunicações'-body, and the ~79K legacy-row false-positive issue is already closed via sync-manifest.parquet as sole source of truth. Rules of the road also document 'Per-item lock + token bucket for IA uploads (in src/djen_backup/archive.py)' -- spot-checked this against the actual module (grep for TokenBucket/token_bucket/rate_limit across src/djen_backup/*.py) and found no class literally named TokenBucket; archive.py has the per-item asyncio.Lock registry (_item_locks/_lock_for) and imports CircuitBreaker from djen_backup.circuit_breaker, but the rate-limiting mechanism referenced as 'token bucket' in CLAUDE.md/comments needs to be traced to its actual implementation before treating it as a literal type -- flagged for the goal-selection step below rather than assumed to be a doc/code drift bug on a first pass. File map (engine.py/manifest.py/djen.py/archive.py/retry.py/__main__.py, scripts/render_queries.py) still matches the tree. No other drift found between documented contracts and code in this pass."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada, via as instruções de projeto fornecidas pelo sistema. Nenhuma divergência de correção encontrada. Um ponto para investigar no passo de seleção de goal: CLAUDE.md menciona "token bucket" para uploads na IA, mas não há classe `TokenBucket` literal em `src/djen_backup/archive.py` -- precisa ser rastreado até a implementação real antes de tratar como bug de documentação.
