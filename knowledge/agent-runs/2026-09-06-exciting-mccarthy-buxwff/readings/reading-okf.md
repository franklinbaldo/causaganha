---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-buxwff-reading-okf"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-06-exciting-mccarthy-uwm65t/run.md (previous round, closed #1217); knowledge/backlog/issue-951.md; web/src/layouts/ogImage.test.ts (raw-source-parsing test pattern for Layout.astro)"
finding: "Prior round (uwm65t) closed #1217, promoting /agentes' four job cards to copyable example questions, and its next_move explicitly anticipated that the repo owner might raise a follow-up product call about the golden fixture — instead the owner opened a new, complementary issue (#1219) about discoverability of the whole /agentes surface from the home page, which this round picks up. knowledge/backlog/issue-951.md records that #951 (building /agentes itself) is blocked on an infra/hosting decision for a remote MCP endpoint — #1219 explicitly does NOT depend on that (its own body: 'não depende de #950 e não deve anunciar endpoint HTTP ainda'), confirming this round's selected work has no such blocker. web/src/layouts/ogImage.test.ts already establishes the pattern this round reuses for its own contract tests: read a .astro file's raw source with readFileSync and assert against it with regex/string matching (no full Astro render needed) — the same methodology tests/causaganha_mcp/test_web_agents_contract.py uses for agentes.astro. No OKF type/schema change is needed for this round's selected work; it is pure product code (web navigation/home copy) plus two new co-located Vitest contract tests, following an established pattern rather than inventing one."
---

# Leitura do conhecimento OKF

A rodada anterior (uwm65t) fechou #1217; o dono do repositório abriu na sequência #1219, pedindo para tornar a superfície `/agentes` descobrível a partir da home — sem depender da decisão de hospedagem MCP que bloqueia #951 (confirmado no próprio corpo da issue). O padrão de teste já usado em `ogImage.test.ts` (ler o `.astro` bruto com `readFileSync` e comparar via regex) é reaproveitado nos dois novos testes desta rodada, em vez de inventar um mecanismo novo. Nenhuma mudança de schema OKF é necessária.
