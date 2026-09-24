---
type: "RunOutcome"
id: "run-outcomes/20260924t202639z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Fixed issue #1615: datajud_status, datajud_facetas and processo_estado now reject any tribunal outside a canonical allowlist (datajud.tribunais.validar_tribunal, sourced from causaganha.config.TRIBUNAIS) before it can reach the DataJud search endpoint path or an IA item id/bundle filename. Proved the injection was real pre-fix (a malicious tribunal='../tjro' actually built api_publica_../tjro/_search and datajud-state-../tjro.zip), fixed it via TDD (RED->GREEN), and verified with a clean full pytest suite + ruff check/format. Issue #1471's handoff was revalidated (IA credentials still absent, 12th+ round) and reframed rather than re-blocked on ceremonially, per this repo's anti-ceremonial-PR policy -- it stays active/unarchived for whenever credentials appear."
next_move: "Open a PR for the tribunal-allowlist fix (issue #1615) against main from this branch; once merged, the remaining open security issues from 2026-09-24 (#1608, #1609, #1610, #1611, #1613, #1614, #1616) are the next natural continuation -- #1610 (validate manifest-derived Parquet URLs) and #1611 (ZIP/JSON resource-exhaustion limits) are similarly self-contained and TDD-shaped. Separately, open PR #1605 (batch27 segmenter ingestion, issue #1050) has a real but narrow merge conflict confined to knowledge/backlog/issue-1050.md's cumulative narrative field -- inspected this round (throwaway worktree, not pushed) and deferred as lower-priority/higher-care-needed than the security fix; a future round should reconcile it by inserting batch27's paragraph into the current blocking_reason/unblock_condition text rather than picking one side."
goals_advanced: ["run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"]
evidence: ["evidence-red-tribunal-injection", "evidence-green-tribunal-allowlist", "evidence-diff-tribunal-allowlist", "evidence-execution-tribunal-allowlist", "evidence-verification-full-suite", "evidence-credential-and-work-survey"]
checks: ["check-handoff-environment", "check-handoff-disposition-resolved", "check-verification-full-suite"]
---

# RunOutcome
