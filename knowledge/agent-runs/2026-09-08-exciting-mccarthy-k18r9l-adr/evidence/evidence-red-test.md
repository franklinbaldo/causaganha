---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-k18r9l-adr-evidence-red-test"
run_id: "2026-09-08-exciting-mccarthy-k18r9l-adr"
goal_id: "2026-09-08-exciting-mccarthy-k18r9l-adr-goal-except-exception-adr"
kind: "test_red"
reference: "uv run pytest -q tests/test_except_exception_policy.py (with the ADR citation temporarily stripped from src/djen_backup/archive.py:264, then restored)"
summary: "After writing the test with all 4 sites already carrying their ADR-citing comments, verified it actually enforces the policy (not a tautology) by temporarily reverting archive.py:264's comment via sed, re-running the test, and confirming it failed with: AssertionError naming exactly 'src/djen_backup/archive.py:264: except Exception as exc:' as the offender. Restored the file from a backup immediately after, re-ran to confirm GREEN again."
---

# Evidence: RED

Teste falhou como esperado quando a citacao do ADR foi removida temporariamente de um dos 4 sites, apontando exatamente esse site como infrator. Arquivo restaurado em seguida.
