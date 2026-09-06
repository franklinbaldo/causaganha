---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-uwm65t-decision-golden-fixture-reuse"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
question: "Which CNJ/query should back the four example questions #1217 asks for, and should it be a live, real CNJ verified against production data, or the project's existing synthetic test fixture?"
choice: "Reuse the exact fixture already treated as this project's de facto golden case across the MCP tool test suite: CNJ 00000010220248220001 (masked 0000001-02.2024.8.22.0001, tribunal tjro), and the texto='dano moral'/fonte='stj' query already used by test_arquivo_estado_teor_contract.py to compose processo_consultar/processo_estado/decisoes_buscar for the same CNJ. Encoded once in src/causaganha_mcp/agents_examples.py, deriving the masked form from the same raw digits via causaganha.processos.cnj.formatar_cnj rather than retyping it, so it cannot drift from the test suite's own fixture."
rationale: "#1217's acceptance criteria explicitly requires 'pelo menos um exemplo usa um golden case/fixture determinístico já conhecido pelo projeto, evitando promessa baseada em dado efêmero' — the risk it names is promising availability based on data that could change or disappear (e.g. 'latest publication this week'). A synthetic-but-deterministic fixture never breaks that promise: it demonstrates the tool call pattern and lets a person verify the agent picked the right tool and reported provenance/limitations honestly, whether or not this particular CNJ resolves to a hit in the live archive. Reusing the exact fixture already exercised end-to-end by test_arquivo_estado_teor_contract.py (rather than inventing a second one) means the example question is protected by the same test that already proves the three tools compose correctly for it, and a future change to that fixture only needs to happen in one place."
---

# Decisão: reaproveitar o CNJ já tratado como fixture dourada, não inventar um novo

O CNJ `0000001-02.2024.8.22.0001` (dígitos `00000010220248220001`) e a busca `texto=\"dano moral\", fonte=\"stj\"` já são a fixture dourada de facto do projeto (usados por `test_arquivo_estado_teor_contract.py` para compor ARQUIVO→ESTADO→TEOR). Reaproveitá-los em `src/causaganha_mcp/agents_examples.py`, derivando a máscara via `formatar_cnj` em vez de retipá-la, evita inventar uma segunda fixture e evita a promessa baseada em dado efêmero que #1217 pede para não fazer.
