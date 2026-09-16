---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-83kr8s-decision-continue-under-legacy-mechanism-despite-deprecation"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal_id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
question: "Merging origin/main into this branch (to resolve the PR going 'behind') pulled in PR #1551, which updates knowledge/agent-runs/index.md and .claude/hourly-loop.md to declare the legacy AgentRun/.claude/agent-run-scaffold.md mechanism -- the exact mechanism this session's own stored prompt explicitly instructs it to use as its first action -- deprecated in favor of a new Wisk runtime (.wisk/knowledge/). This session's stored scheduled-task prompt was written before that migration decision existed. Abort this round's AgentRun report and redo it under Wisk, or finish under the legacy mechanism as already instructed?"
choice: "Finished this round under the legacy AgentRun mechanism as the stored prompt explicitly directs, since the domain work (8 real segmenter documents, already annotated, validated, and PR-ready) is valuable independent of which report format wraps it, and abandoning mid-round to restart under an unfamiliar runtime this session was never instructed to use would waste completed, correct work for a process concern. Did NOT edit .claude/hourly-loop.md or knowledge/agent-runs/index.md to relitigate the deprecation, and did NOT create a second competing report under .wisk/ -- both would be scope creep on top of an already-resolved architectural decision made by a different session. Recorded the finding explicitly (this decision, plus run.md's next_move) so the operator (the human who configured this scheduled task) has a clear, unambiguous signal that the stored prompt for this recurring task now conflicts with the repository's own current policy, since only they can update that stored prompt."
rationale: "Neither continuing nor aborting is free of risk, but the costs are asymmetric here. Continuing risks one more 'legacy-labeled' report in a directory the repo says not to add to anymore -- low cost, since knowledge/agent-runs/index.md itself says the legacy directory is 'preserved for audit and compatibility,' not deleted, and this round's domain contribution (which is what actually matters for #1050) is unaffected either way. Aborting mid-round to adopt Wisk unprompted would mean: (a) discarding fully-validated, already-annotated, ready-to-merge work; (b) operating an orchestration runtime (.wisk/) this session has zero prior context on, under time pressure, with no guidance from its own stored instructions on how to use it correctly -- a much higher chance of a worse mistake than finishing the well-understood mechanism correctly. The stored prompt is also unusually explicit and detailed about the AgentRun mechanism being 'the operational roadmap of the session' -- overriding that unilaterally mid-run, based on a policy change this session had no way to know about at start, is a decision for the human who owns the scheduled task's configuration, not for this session to make silently by switching runtimes on its own initiative."
---

# Decisao: concluir sob o mecanismo legado apesar da depreciacao

O merge de `origin/main` trouxe a PR #1551, que declara o mecanismo
`AgentRun` legado -- exatamente o que o prompt armazenado desta tarefa
agendada instrui como primeira acao da sessao -- depreciado em favor de
um novo runtime Wisk (`.wisk/knowledge/`). Essa decisao de migracao foi
tomada por outra sessao, depois que o prompt desta tarefa agendada foi
configurado. Optei por concluir esta rodada sob o mecanismo legado como
instruido, em vez de abortar trabalho ja validado e pronto para merge
para adotar um runtime que esta sessao nunca foi instruida a usar.
Registrei o achado explicitamente aqui e no `next_move` do relatorio
para que o operador (dono da tarefa agendada) saiba que o prompt
armazenado esta desatualizado em relacao a politica atual do
repositorio.
