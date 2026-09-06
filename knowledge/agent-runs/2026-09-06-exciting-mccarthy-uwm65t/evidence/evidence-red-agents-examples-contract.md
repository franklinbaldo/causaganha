---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-uwm65t-evidence-red-agents-examples-contract"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
kind: "test_red"
reference: "uv run pytest tests/causaganha_mcp/test_agents_page_examples_contract.py -v (before web/src/pages/agentes.astro embedded any CopyQuestionExample markup)"
summary: "tests/causaganha_mcp/test_agents_page_examples_contract.py was written before agentes.astro had any example markup. 1 failed, 3 passed: test_agents_page_shows_the_canonical_example_for_every_public_job failed with the parsed page yielding an empty dict ({}) against the four canonical questions from src/causaganha_mcp/agents_examples.py, confirming the test genuinely exercises not-yet-built markup rather than passing vacuously. The other three tests (tool registered in build_server(), no unpublished fonte named, exactly one example per job) already passed because they only exercise the Python module itself, independent of the page."
---

# RED: página ainda não embutia os exemplos

`test_agents_page_shows_the_canonical_example_for_every_public_job` falhou como esperado (dict vazio) antes de `agentes.astro` ganhar o marcado `CopyQuestionExample`, confirmando que o teste testa algo real.
