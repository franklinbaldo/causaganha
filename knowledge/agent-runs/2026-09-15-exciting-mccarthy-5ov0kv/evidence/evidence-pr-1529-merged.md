---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5ov0kv-evidence-pr-1529-merged"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: "2026-09-15-exciting-mccarthy-5ov0kv-goal-scale-segmenter-reviews"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1529 ; merge sha 7212833b56678c79db801c07b0d870a1eef8f94e"
summary: "PR #1529 mesclada (squash 7212833b56678c79db801c07b0d870a1eef8f94e) apos 11/11 checks de CI ficarem verdes (CodeQL, compare-product-surfaces, validate, web, lint, tests (tjro), GitGuardian, Analyze x4). Codex Security Review completo sem achados bloqueantes. mergeable_state=clean."
---

# Evidência: PR #1529 mesclada

Primeiro push (`9a23b36`) disparou CI com `validate` e `tests (tjro)`
RED: `uv run python scripts/generate_okf_domain_models.py` no CI detectou
que `src/causaganha_mcp/_generated/domain_models.py` ainda estava
desatualizado em relação ao bundle final, porque o arquivo
`evidence-generated-files-regenerated.md` (que também usa `goal_id: null`
em `AgentEvidence`, o segundo caso do bundle inteiro) foi adicionado
*depois* da primeira regeneração desta rodada. Root-caused localmente
(`uv run python scripts/generate_okf_domain_models.py` /
`generate_okf_zod_schemas.py` reproduziram o mesmo diff de 1 linha que o
CI reportou), corrigido com um segundo commit (`1e362db`) que regenera os
dois arquivos derivados contra o estado final do bundle, validado
localmente (`uv run pytest -q` completo, `ruff check`/`format --check`,
`okf-parser check`) antes do push. `mcp__github__pull_request_read(method=
get_check_runs)` no commit `1e362db`: 11/11 `completed`/`success`.
`mcp__github__merge_pull_request(merge_method=squash,
expectedHeadSha=1e362db28deb47666ba1d8dc298712179dee80b0)` retornou
`{"sha":"7212833b56678c79db801c07b0d870a1eef8f94e","merged":true}`. Pós-merge,
`uv run python scripts/segmenter_governance_status.py` em `origin/main`
confirma `review_count: 27, evaluation_eligible_count: 27`.
