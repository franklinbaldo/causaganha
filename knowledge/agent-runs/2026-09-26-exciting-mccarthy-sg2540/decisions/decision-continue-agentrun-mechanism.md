---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-sg2540-decision-continue-agentrun-mechanism"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
question: "Should this round still create a new AgentRun report under knowledge/agent-runs/, given knowledge/agent-runs/index.md and .claude/hourly-loop.md both state the mechanism is legacy and superseded by the Wisk runtime for CausaGanha's hourly loop?"
choice: "Continue creating this round's AgentRun report per this session's own scheduled prompt."
rationale: "The Wisk-migration notice targets the hourly loop (a separate automation, evidenced by same-day rounds pg2bcv/uq3be8 in knowledge/backlog/issue-1051.md already using .wisk/knowledge/experiences/runs/ instead of an AgentRun). This session's own scheduled prompt -- stored ahead of time by an authorized session on this account -- explicitly and repeatedly instructs creating a new AgentRun from .claude/agent-run-scaffold.md as the session's first action, and every prior round today under this exact branch prefix (claude/exciting-mccarthy-*) did the same, producing knowledge/agent-runs/ reports well after the Wisk notice was already in place. Deviating unilaterally from an established, repeated pattern this session's own task explicitly requires -- based on a notice aimed at a different automation -- would break continuity without a clear signal that it's the right call. Recorded here rather than silently resolved so a future round (or the user) can correct course if this reading is wrong."
---

# Decision: keep using the AgentRun mechanism this round

See `readings/reading-okf.md` for the full discovery. Short version:
two automations appear to touch this repo -- a Claude-Code-native
scheduled loop (this session, `claude/exciting-mccarthy-*` branches,
still following the `AgentRun` contract) and a separate Wisk-based
hourly loop (already migrated, per `.claude/hourly-loop.md`). Chose
continuity with this session's own established pattern over unilaterally
adopting a notice written for the other automation.
