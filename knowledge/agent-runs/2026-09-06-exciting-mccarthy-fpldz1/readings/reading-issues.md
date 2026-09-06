---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-fpldz1-reading-issues"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN) as of 2026-09-06T18:20Z; knowledge/backlog/ (17 issue-<n>.md files, last_verified_run_id=2026-09-06-exciting-mccarthy-o86vcs at 2026-09-06T17:52Z)"
finding: "18 open issues. The same 17 already catalogued in knowledge/backlog/ remain blocked with no GitHub state change since round o86vcs verified them ~30 minutes before this round started (884/886/887/1050/1051/1053/1054/1055/1056/1057/1047 — ml_data_work needing GPU/annotation rounds; 1011/1022/985 — credentials-blocked TCU/TSE Internet Archive publication; 950/951 — infra_decision requiring the repo owner; 1093 — deprioritized_by_owner), so these are cited rather than re-investigated. One genuinely new issue: #1225 'web(processo): permitir continuar a consulta no agente com o CNJ já contextualizado', filed 2026-09-06T18:01:13Z (after round o86vcs's own reading, before this round started) by the repo owner and explicitly marked 'READY para IMPLEMENTAÇÃO. Slice web pequeno, sem credenciais e sem dependência operacional externa.' It asks that ProcessoLookup.svelte's 'found' state gain a secondary action that copies a natural-language question (containing the already-queried CNJ) for continuing the investigation via the MCP-connected agent introduced by #1217/#1219, with an onboarding link to /agentes, without any network call and while keeping this action semantically distinct from the existing 'Copiar link' and 'Copiar referência' actions. It explicitly asks to reuse or test parity with the #1217 example-question authority (causaganha_mcp/agents_examples.py) rather than inventing an untested parallel string, and lists nine concrete acceptance criteria plus a small, self-contained implementation directive."
---

# Leitura das issues abertas

Dezoito issues abertas: as mesmas 17 bloqueadas confirmadas pela rodada anterior (o86vcs), sem mudança de estado, mais uma issue nova (#1225) aberta minutos antes desta rodada começar — pronta para implementação, sem dependência de credenciais ou infraestrutura externa, e com critérios de aceite explícitos. Esta é a candidata natural de trabalho da rodada.
