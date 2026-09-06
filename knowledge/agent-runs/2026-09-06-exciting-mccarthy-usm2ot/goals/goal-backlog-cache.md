---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-usm2ot-goal-backlog-cache"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
goal: "Model and populate a durable 'blocked backlog' knowledge type (BacklogItem) that records, per open GitHub issue, why it is currently blocked/deprioritized and when that was last verified — so a future round can read it instead of re-deriving the same rejection reasoning from scratch."
rationale: "At least ~10 consecutive rounds (documented in yigsua, 6x90uc, m65xwe and this round's own reading-issues) have independently re-read and re-justified the exact same 17 blocked/deprioritized issues, because the OKF model has no place for a fact to outlive a single round's AgentReading. Round 6x90uc named this gap explicitly and round m65xwe repeated it unresolved, both times deferring it as 'needs a product-owner call' — but recording a verified fact ('this issue needs credentials absent from this env, checked on date X') is a knowledge-model fix, not a decision about backlog priority, so it is in scope for this loop to build without external sign-off."
success_signal: "knowledge/backlog/ exists with one BacklogItem file per currently-open issue (17), each with a category, blocking_reason, unblock_condition and last_verified_run_id pointing at this round; a new pytest test (tests/knowledge/test_backlog.py) written RED first (fails because knowledge/backlog/ does not exist) then GREEN validates every BacklogItem's issue_number is unique, every status/category value is one declared in the schema, and every last_verified_run_id resolves to a real AgentRun directory under knowledge/agent-runs/; okf-parser check stays conformant (0 diagnostics) with the new BacklogItem PK/FK wired into okf.schema.sql; .claude/hourly-loop.md is updated to instruct a future round to consult knowledge/backlog/ before re-deriving open-issue rejection reasoning."
status: "achieved"
---

# Goal: registro durável de backlog bloqueado

Fechar a lacuna nomeada por duas rodadas anteriores (6x90uc, m65xwe) sem resolver: um cache de conhecimento que sobrevive a uma única rodada, guardando por que cada issue aberta está bloqueada e quando isso foi verificado pela última vez.
