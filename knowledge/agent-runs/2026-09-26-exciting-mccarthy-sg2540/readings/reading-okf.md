---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-sg2540-reading-okf"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
subject: "okf_knowledge"
reference: "knowledge/backlog/issue-1051.md, knowledge/backlog/issue-1050.md, .claude/agent-run-scaffold.md, knowledge/agent-runs/index.md, .claude/hourly-loop.md, uv run okf-parser check knowledge --relational-schema okf.schema.sql"
finding: "OKF bundle conformant at session start (0 diagnostics, 2580 concepts). Discovered a genuine tension: knowledge/agent-runs/index.md and .claude/hourly-loop.md both declare the AgentRun/AgentReading/.../AgentCheck mechanism legacy, superseded by a separate 'Wisk' runtime (uv run wisk start) for the hourly loop, and explicitly say not to create new AgentRuns. This session's own scheduled prompt, however, explicitly instructs creating a new AgentRun from the scaffold -- and every prior round today under this exact branch-naming pattern (exciting-mccarthy-*) did so, evidently as a separate, still-live automation track from the Wisk hourly loop. Followed precedent: continued using the AgentRun mechanism for this round (see decision-continue-agentrun-mechanism), while flagging the tension here rather than silently picking a side."
---

# Reading: knowledge OKF bundle

Ran `uv run okf-parser check knowledge --relational-schema okf.schema.sql`
at session start: `{"concept_count": 2580, "conformant": true,
"diagnostics": [], "markdown_count": 2583, "reserved_count": 3}` (see
`checks/check-okf-parser-baseline.md`).

Read `knowledge/backlog/issue-1051.md` in full -- the authoritative,
continuously-updated operational narrative for this round's chosen
goal, maintained by every prior #1051 round (`ns7mbo` through
`pg2bcv`/`uq3be8`). It documents the exact method this round followed:
scan single-annotated/`seeded_with=='none'`/unreviewed candidates,
SIMULATE `assign_splits` (isolated then joint) before annotating,
dispatch genuinely independent second annotations (Agent tool,
`model=haiku`), verify mechanically (verbatim-fidelity reconstruction
+ `mechanical.validate_record`) before trusting any subagent's
self-check, adjudicate disagreements against the guideline's own
rules, and re-run the *full* test suite plus
`scripts/segmenter_semantic_audit.py` during adjudication (not only at
the end) since an ingested annotation's or review's own span choice
can trip a zero-tolerance finding.

**Also read `knowledge/agent-runs/index.md` and
`.claude/hourly-loop.md`.** Both state, in Portuguese, that the
`AgentRun`/`AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`/
`AgentCheck` mechanism and `knowledge/agent-runs/` are historical
legacy, that CausaGanha's hourly loop now runs exclusively through the
Wisk runtime (`uv run wisk start`), and explicitly instruct: "não crie
novos `AgentRun`... aqui." This is a real, current statement in the
repository's own knowledge, not stale content -- `knowledge/backlog/
issue-1051.md` itself records several *same-day* rounds (`pg2bcv`,
`uq3be8`) that already migrated to the Wisk runtime instead of writing
an `AgentRun`.

At the same time, this session's own scheduled prompt (stored ahead of
time by an authorized session on this account) explicitly instructs
creating a new `AgentRun` from `.claude/agent-run-scaffold.md` as the
first action, and every prior round today sharing this exact branch
prefix (`claude/exciting-mccarthy-*`: `uz8msx`, `ku8qje`, `p08457`,
`kgxf50`, `bomtmk`) did exactly that, continuing to produce
`knowledge/agent-runs/` reports well after the Wisk-migration notice
was already in place. The most coherent reading is that two separate
automations operate on this repository -- this session's own
Claude-Code-native scheduled loop (still following the `AgentRun`
contract per its own stored prompt) and a distinct Wisk-based hourly
loop (already migrated) -- rather than this session's prompt being
simply stale. Recorded as `decision-continue-agentrun-mechanism`
rather than silently resolved.
