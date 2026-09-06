---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-uwm65t-evidence-green-agents-examples-contract"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
kind: "test_green"
reference: "uv run pytest tests/causaganha_mcp/test_agents_page_examples_contract.py tests/causaganha_mcp/test_web_agents_contract.py -v"
summary: "After adding <CopyQuestionExample question=\"...\"> markup (verbatim from src/causaganha_mcp/agents_examples.py) inside each of the four job <article> cards in web/src/pages/agentes.astro, all 10 tests pass: the 4 new contract tests (page shows canonical wording verbatim, every example's tool is registered in build_server(), decisoes_buscar's example never names an unpublished fonte, exactly one example per job) plus the 6 pre-existing test_web_agents_contract.py tests (unaffected by this change) are green."
---

# GREEN: 10/10 testes de contrato passam

Depois de embutir `<CopyQuestionExample question=\"...\">` em cada card, os 4 testes novos e os 6 testes já existentes de `test_web_agents_contract.py` passam juntos.
