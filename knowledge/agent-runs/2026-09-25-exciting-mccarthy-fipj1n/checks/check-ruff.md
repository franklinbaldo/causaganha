---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-fipj1n-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
command: "uv run ruff check src/tjro_juris/manifest.py tests/tjro_juris/test_juris_manifest.py tests/causaganha/decisoes/test_published.py && uv run ruff format --check src/tjro_juris/manifest.py tests/tjro_juris/test_juris_manifest.py tests/causaganha/decisoes/test_published.py"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-fipj1n-evidence-green-mes-ano-validation"
summary: "Primeira execução pegou TRY301 (raise dentro de try deveria estar numa função interna) em manifest.py; corrigido extraindo _validate_mes_ano. Segunda execução: ruff check reportou 'All checks passed!' e ruff format --check reportou os 3 arquivos já formatados."
---

# Check: ruff lint + format

`ruff check` reportou "All checks passed!" e `ruff format --check`
reportou os 3 arquivos tocados já formatados corretamente, após corrigir
um TRY301 (raise extraído para `_validate_mes_ano`).
