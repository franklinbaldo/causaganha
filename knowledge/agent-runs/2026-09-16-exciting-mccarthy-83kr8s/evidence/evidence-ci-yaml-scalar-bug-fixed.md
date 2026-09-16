---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-83kr8s-evidence-ci-yaml-scalar-bug-fixed"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal_id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
kind: "ci"
reference: "CI check 'tests (tjro)' run 35094754996/job/104789232863 on PR #1552, failing with RuntimeError: knowledge bundle is not OKF-conformant across 14 tests in tests/causaganha_mcp/test_causaganha_status.py, test_okf_pipeline_catalog.py, test_status_contract.py"
summary: "run.md's next_move field held a multi-paragraph value inside a double-quoted YAML scalar with embedded literal newlines and zero-indented continuation/blank lines -- invalid per the YAML spec's quoted-scalar folding rules. `uv run okf-parser check` (the CLI this round used throughout) never flagged it, but `causaganha_mcp.knowledge.load_bundle` (a separate, stricter YAML loader that CI's tests/causaganha_mcp/test_causaganha_status.py etc. depend on transitively via CausaganhaStatusResult) does, and CI caught it. Fixed by collapsing next_move to a single line (no embedded newlines), matching the style already used by result_summary and every prior round's next_move in this lineage. Verified locally with BOTH loaders after the fix: `causaganha_mcp.knowledge.load_bundle(...).is_conformant` is True (previously False), `uv run okf-parser check` conformant=true (was already true before and after, confirming it does not exercise this class of error), and the 14 previously-failing tests now pass locally (`uv run pytest tests/causaganha_mcp/test_causaganha_status.py tests/causaganha_mcp/test_okf_pipeline_catalog.py tests/causaganha_mcp/test_status_contract.py -q`)."
---

# Evidencia: bug de YAML pego pelo CI, corrigido

`next_move` tinha um escalar YAML entre aspas duplas com paragrafos
multi-linha e linhas de continuacao/em branco sem indentacao --
invalido pela spec YAML. `okf-parser check` (usado a rodada toda) nao
pegou; o loader mais estrito usado por `causaganha_mcp.knowledge`
(exercido pelos testes `tests (tjro)` do CI) pegou. Corrigido
colapsando `next_move` para uma unica linha. Confirmado localmente com
os dois loaders e com os 14 testes que falhavam no CI, agora verdes.
