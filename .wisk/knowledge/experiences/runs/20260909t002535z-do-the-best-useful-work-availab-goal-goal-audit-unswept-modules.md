---
type: "RunGoal"
id: "run-goals/20260909t002535z-do-the-best-useful-work-availab/goal-audit-unswept-modules"
run: "runs/20260909T002535Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Audit the remaining unswept top-level src/causaganha/ modules (consolidate, pipeline, storage, publicacoes, analysis) and the web/ TypeScript lib tree for a real, currently-live bug, following this loop's established audit pattern (duplicated classification logic, calendar-day vs business-day mismatches, static-plan-vs-actual-execution drift, dead code with silently-broken references), fix it via TDD (RED test reproducing the bug, then GREEN), and land a PR."
rationale: "Issue backlog (17 issues) reconfirmed identical to prior rounds and still environment-blocked (segmenter needs GPU/annotation infra; TCU/TSE need credentials or are network-blocked; MCP remote endpoint needs an infra decision). Zero open PRs, zero active handoffs (18/18 archived), zero registered skills. Per the wiki's continuous-loop-operational-invariants.md and the immediately prior run's own next_move, decisoes/ and processos/ were already audited and found substantially clean; consolidate/pipeline/storage/publicacoes/analysis and the web TypeScript tree remain unswept and are the best-available continuity path to a real product advance this round."
success_signal: "A concrete bug is found and reproduced by a failing (RED) test; the fix makes it pass (GREEN); the full relevant test suite (pytest and/or vitest), lint, and typecheck stay green; a PR is opened with the fix."
status: "active"
---

# RunGoal
