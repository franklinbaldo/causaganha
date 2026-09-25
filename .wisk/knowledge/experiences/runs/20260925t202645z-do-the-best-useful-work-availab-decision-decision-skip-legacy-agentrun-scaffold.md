---
type: "RunDecision"
id: "run-decisions/20260925t202645z-do-the-best-useful-work-availab/decision-skip-legacy-agentrun-scaffold"
run: "runs/20260925T202645Z-do-the-best-useful-work-available-in-this-reposi"
question: "The scheduled task prompt for this session instructs creating a new legacy AgentRun report from .claude/agent-run-scaffold.md and running okf-parser check to drive the round via that mechanism. Should this session follow that stale instruction or the repository's current convention?"
decision: "Do not create a new legacy AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck instance. Follow .claude/hourly-loop.md instead: run 'uv run wisk init .' (needed once per fresh checkout since .wisk/manifest.json, .wisk/specs/, .wisk/knowledge/system/ are gitignored) then 'uv run wisk start', and drive the round through the Wisk LoopRun/SessionType/RunSpec contracts."
rationale: "knowledge/agent-runs/index.md explicitly states: 'O loop horario do CausaGanha migrou para WikiSkill. Nao crie novos AgentRun... Consulte .claude/hourly-loop.md.' That file confirms the AgentRun mechanism is legacy-only (preserved for audit, never for new rounds) and that 'wisk start' is the only golden path. The scheduled prompt itself is a stored instruction that predates this migration and is exactly the kind of stale automation .claude/hourly-loop.md's own migration note anticipates; project convention (checked into the repo, applying explicitly to this exact scheduled-loop scenario) takes precedence over the outdated scaffold instructions per the system's own CLAUDE.md-override rule."
---

# RunDecision
