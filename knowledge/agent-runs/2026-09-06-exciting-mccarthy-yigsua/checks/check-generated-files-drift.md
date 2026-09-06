---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-yigsua-check-generated-files-drift"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
command: "uv run --no-sync python scripts/generate_okf_domain_models.py && uv run --no-sync python scripts/generate_okf_zod_schemas.py; git status --short — run twice, before and after conforming this round's AgentGoal/AgentDecision/AgentCheck field names to knowledge/.okf/specs/agent*.schema.sql, and with both okf-parser 0.45.6 (pinned by .github/workflows/okf.yml's validate job) and 0.45.8 (what a fresh uv sync resolves) installed locally to rule out a version-drift cause"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-yigsua-evidence-generated-files-zero-diff"
summary: "Confirmed the tests/causaganha_mcp/test_okf_domain_models.py and tests/web/test_generate_okf_zod_schemas.py failures seen mid-round were caused by this round's own invented field names, not by okf-parser version drift (both 0.45.6 and 0.45.8 reproduced the same diff before the fix and the same zero-diff after it). Regenerating after conforming field names produces byte-identical output to the committed generated files."
---

# Check — drift dos arquivos gerados (causa raiz)

Confirmado, com 0.45.6 e 0.45.8, que a causa era os nomes de campo inventados nesta rodada — não uma mudança de versão do `okf-parser`. Diff zero após a correção.
