---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-qnpypw-reading-okf"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/ (9 prior completed rounds today, 2026-09-05) + `uv run okf-parser check knowledge --relational-schema okf.schema.sql`"
finding: "Before this round's own readings/goals existed, `okf-parser check` reported the bundle conformant (0 diagnostics, 180 concepts). Once this round's scaffold was copied and the four readings written, the same check correctly flagged 3 dangling foreign keys (AgentReading.run_id -> AgentRun.id) because run.md still held the scaffold's empty AgentRun stub — exactly the intended scaffold->check->fill loop described in .claude/agent-run-scaffold.md. Reading the 9 prior rounds' run.md files (qvwrkl, e9r0mj, ich5gz, ejibsp, 1fxd8b, 9xpeua, fnt3vx, sf5rj3, and the two-PR reboot collision discovered live rather than in a report) shows a consistent, hard-won discipline: verify every 'open' backlog item against the live repository/CI/artifact state before trusting an issue's checklist or a prior round's characterization, because several supposedly-open gaps (#1107, three of #924's five dead-code claims, #1048's remaining checklist item, #1052's entire checklist) turned out to already be resolved by merged work that never referenced the issue number. #1042 was the one item explicitly left dangling across at least 5 of those prior rounds' next_move notes, each time for the same single reason: the pipeline/publish/read-back proof was solid, but nobody had yet compared processo_consultar (MCP) against /processo (web) for the same real, non-fixture CNJ. This round closes that specific, long-standing gap."
---

# Leitura de conhecimento OKF

O check confirmou o loop scaffold→check→preencher funcionando: assim que o scaffold foi copiado, o `okf-parser` acusou corretamente as FKs pendentes de `AgentReading.run_id`, orientando o preenchimento do restante do relatório. As 9 rodadas de hoje mostram um padrão recorrente de "verificar ao vivo antes de aceitar uma lacuna como real" — a #1042 era a lacuna mais persistente, deixada em aberto por pelo menos 5 rodadas anteriores, sempre pelo mesmo motivo pontual: faltava comparar `processo_consultar` (MCP) com `/processo` (web) para o mesmo CNJ real. Esta rodada fecha exatamente essa lacuna.
