---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-hv2ep2-decision-follow-scheduled-scaffold-despite-deprecation"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal_id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
question: "knowledge/agent-runs/index.md and .claude/hourly-loop.md both declare the legacy AgentRun mechanism deprecated in favor of Wisk, but this session's stored task prompt hard-codes the AgentRun scaffold as mandatory and uv run wisk start is live-blocked (no-eligible-session). Create the AgentRun report anyway, or escalate/refuse?"
choice: "Create the AgentRun report anyway, following the exact precedent of every round today (83kr8s, c4y4rc, k5wsee, and others) that hit the same conflict. Do not send a new proactive notification -- the conflict is already known (2+ prior PushNotifications) and nothing material changed since the last evaluation (wisk still blocked, no human comment on the conflict)."
rationale: "The scheduling owner's stored prompt is the authority for how this specific session should behave; the deprecation notice asks future *scheduling* to move to Wisk, not this session to refuse its own instructions. Escalating again with no new fact would be noise, not signal -- the run instructions explicitly say to only escalate if something actually changed (wisk becomes eligible, or a human comment appears)."
---

# Decisão: seguir o scaffold agendado apesar da depreciação

Mesma decisão de toda rodada concorrente de hoje: manter o mecanismo
AgentRun para este relatório específico, registrar a tensão nas leituras
(`reading-okf`), e não repetir uma notificação já feita sem fato novo.
