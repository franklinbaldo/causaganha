---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-5ov0kv-evidence-generated-files-regenerated"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: null
kind: "ci"
reference: "web/src/lib/processoConsultar.gen.ts ; src/causaganha_mcp/_generated/domain_models.py"
summary: "Apos completar run.md, uv run pytest -q mostrou 2 falhas reais (nao do scaffold): os testes que comparam os arquivos gerados (Zod/domain-model) contra a forma inferida do bundle OKF atual. Causa raiz: AgentCheck.goal_id se torna genuinamente nullable pela primeira vez de forma detectavel (checks/check-ruff.md desta rodada e o 2o AgentCheck do bundle inteiro, depois de to0ars em 14/09, a usar goal_id: null). Corrigido regenerando os dois arquivos via seus scripts oficiais (nao editados a mao)."
---

# Evidência: regeneração dos arquivos derivados do OKF após goal_id nullable

`uv run python scripts/generate_okf_zod_schemas.py` e `uv run python
scripts/generate_okf_domain_models.py` reescreveram
`web/src/lib/processoConsultar.gen.ts` e
`src/causaganha_mcp/_generated/domain_models.py` (1 linha cada):
`AgentCheckConcept.goal_id: str` → `str | None` (Python) e
`.describe("references AgentGoal(id)").optional()` →
`.describe("references AgentGoal(id)").nullable().optional()` (Zod). O
schema relacional (`okf.schema.sql`) sempre permitiu `goal_id` nulo em
`AgentCheck` — a forma inferida só reflete essa possibilidade quando pelo
menos uma instância real do bundle a usa; até esta rodada só uma instância
existia (`to0ars`, 14/09), o suficiente para a nullability já constar do
schema Pydantic mas, aparentemente, não para o exportador Zod/domain-model
recalcular na regeneração anterior. `git diff --stat` confirma exatamente
1 linha alterada em cada arquivo gerado, sem nenhuma outra mudança de
forma. `uv run pytest -q` (suíte completa) após a regeneração: 100% verde.
