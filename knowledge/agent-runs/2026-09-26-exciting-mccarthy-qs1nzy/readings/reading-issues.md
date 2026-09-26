---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-qs1nzy-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-qs1nzy"
subject: "open_issues"
reference: "GitHub issues, franklinbaldo/causaganha (mcp__github__list_issues, state=OPEN, 21 total) + knowledge/backlog/issue-1050.md + knowledge/backlog/issue-1051.md"
finding: "21 open issues, same count as round bomtmk. #1051 remains the only unblocked, actively-progressing track with a concrete, mechanically-checkable next step and no external-credential dependency -- but this session's own tool surface cannot execute #1051's established method (dispatching an independent-annotation subagent), a session-specific blocker distinct from anything a prior round hit. #950/#951/#1093 and the Parquet/CNJ/TCU/TSE cluster (#1470/#1469/#1471/#1472/#1468/#1022/#985) remain blocked on GCP/IA credentials this session lacks, per 16+ prior rounds -- not re-investigated in depth, no new activity signal."
---

# Reading: open issues + segmenter backlog state

`mcp__github__list_issues` (state=OPEN, 21 total) plus a full read of
`knowledge/backlog/issue-1050.md` and `knowledge/backlog/issue-1051.md`.

**#1051** (`segmenter: build an independently annotated validation set
for model selection`) -- status `unblocked`. Live
`scripts/segmenter_governance_status.py` at session start (on merged
`main`, commit `103ad9b`, round uq3be8's PR #1677): `document_count=197`,
`review_count=43`, `val_count=30` (at its RFC 0012 ceiling),
`test_count=13` (of a 30 floor) -- exactly matching `issue-1051.md`'s
last-recorded numbers. The backlog's established method (5 prior
same-day rounds) is: scan single-annotated/`seeded_with=='none'`/
unreviewed candidates, simulate `assign_splits` before spending effort,
dispatch a genuinely independent second annotation via an Agent-tool
subagent (`model=haiku`), verify mechanically, adjudicate, re-run the
full suite.

**This round could not execute that method's subagent-dispatch step.**
No `Task`/`Agent` tool is present in this session's tool surface
(`ToolSearch` for `Agent`/`Task`/`SpawnAgent`/`CreateAgent`/`Dispatch`
returned nothing), and attempting the equivalent via a nested `claude -p
--model haiku` CLI subprocess was denied outright by the environment's
own auto-mode classifier (`[Create Unsafe Agents]`), with an explicit
instruction not to retry via different flags/tools/hosts. This is a
session-specific tooling gap, not a repository or #1051-method problem
-- concurrent rounds working the same issue *did* have Agent-tool access
(see PR #1678's description: "5 parallel Agent-tool subagents,
model=haiku"). See `decisions/decision-subagent-tool-unavailable.md`.

**#1050** (`segmenter: repair and scale the real training corpus with
agent annotation`) -- status `unblocked`. Corpus-scale ceiling already
reached 30/30 since round `ku8qje`; also gated on the same subagent
capability for first-pass annotation, so equally unreachable this round.

**Re-confirmed blocked, not re-investigated (established by 16+ prior
rounds):** #950 (`product(mcp): disponibilizar endpoint remoto`) and
downstream #951/#1093 -- needs GCP Cloud Run deploy credentials this
session lacks. #1470/#1471/#1472/#1468/#1469/#1022/#985 (Parquet/CNJ
regeneration, TCU/TSE Internet Archive publication) -- need live IA/GCP
write access this session does not have.

**#1053-1057/#884/#886/#887** -- longer-horizon segmenter experiment
issues gated on the #1051 val/test floor being met first. Not
selectable yet.

**Decision driver:** given the subagent-dispatch blocker, this round
pivoted to formalizing the #1051 candidate-selection method itself
(`scripts/segmenter_adjudication_candidates.py`) -- a real, tested,
committed replacement for the ad hoc scratch script every one of the
six prior #1051 rounds wrote fresh -- rather than fabricating a
second annotation under a false `model_family` label to force the
numeric floor forward dishonestly.
