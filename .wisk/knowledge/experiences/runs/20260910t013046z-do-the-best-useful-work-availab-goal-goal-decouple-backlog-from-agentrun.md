---
goal: "Decouple knowledge/backlog/'s BacklogItem.last_verified_run_id provenance from the deprecated AgentRun mechanism so ongoing Wisk rounds can keep re-verifying blocked issues without creating new legacy knowledge/agent-runs/ directories."
id: "run-goals/20260910t013046z-do-the-best-useful-work-availab/goal-decouple-backlog-from-agentrun"
kind: "task-advance"
rationale: "The backlog cache's whole purpose is to let a round re-verify a blocked issue's reason and record when that happened (knowledge/backlog/index.md's own 'como manter' instructions). Its schema (okf.schema.sql) and tests/knowledge/test_backlog.py hard-require last_verified_run_id to resolve to knowledge/agent-runs/<id>/run.md, i.e. the legacy AgentRun type. .claude/hourly-loop.md and this repo's own WikiEntry (continuous-loop-operational-invariants) both say new rounds must not create AgentRuns anymore -- they use Wisk's LoopRun instead. So no round following current guidance can ever update last_verified_run_id again: the cache is frozen at 2026-09-07 provenance forever, silently defeating its own stated purpose the moment the migration note was written. This round live-reverified 3 credential/network-blocked issues (#1011, #1022, #985 -- still no IAS3 keys, still 403 from TSE's Akamai front) and hit exactly this wall trying to record it."
run: "runs/20260910T013046Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "RED: pytest tests/knowledge/test_backlog.py fails when a BacklogItem's last_verified_run_id is set to a Wisk LoopRun reference (the only kind of round this repo produces now). GREEN: the same test suite passes after last_verified_run_id accepts either a legacy AgentRun path or a Wisk LoopRun reference, and issue-1011.md/issue-1022.md/issue-985.md carry this round's real wisk: provenance and current timestamp."
type: "RunGoal"
---

# RunGoal
