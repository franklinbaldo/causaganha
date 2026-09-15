---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5ov0kv-evidence-pr-1527-merged"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1527 ; merge sha d7658aa5b18d2baa6ecb8282c29e97a09b811252"
summary: "PR #1527 ('feat(segmenter): scale RFC 0012 ReviewRecords 23->25 (#1051)', branch claude/exciting-mccarthy-bc9ae6) mesclada por esta rodada via mcp__github__merge_pull_request (squash), apos confirmar 10/10 checks de CI verdes e mergeable_state=clean."
---

# Evidência: merge da PR #1527

`mcp__github__pull_request_read(method=get_check_runs, pullNumber=1527)`
mostrou 10/10 checks `completed`/`success` (CodeQL, web, lint,
tests (tjro), validate, Analyze x4, GitGuardian Security Checks) e
`mcp__github__pull_request_read(method=get_comments)` mostrou o Codex
Security Review `completed` sem achados bloqueantes
(`mergeGateEnabled":false`). `mcp__github__merge_pull_request(owner=
franklinbaldo, repo=causaganha, pullNumber=1527, merge_method=squash,
expectedHeadSha=e813299b0656cc242d04a0ec73b9b1b595f9df85)` retornou
`{"sha":"d7658aa5b18d2baa6ecb8282c29e97a09b811252","merged":true,
"message":"Pull Request successfully merged"}`. Pós-merge, `git fetch
origin main && git log origin/main -1 --oneline` confirmou
`d7658aa feat(segmenter): scale RFC 0012 ReviewRecords 23->25 (#1051)
(#1527)` em `main`, e `uv run python
scripts/segmenter_governance_status.py --store data/segmenter` reportou
`review_count: 25, evaluation_eligible_count: 25` (de `document_count: 61,
annotation_count: 100`).
