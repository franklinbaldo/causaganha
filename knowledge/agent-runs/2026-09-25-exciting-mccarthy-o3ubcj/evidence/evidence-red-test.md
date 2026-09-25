---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-o3ubcj-evidence-red-test"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts (24 testes novos) contra o processoCnj.ts anterior ao goal (git stash da implementação, mantendo os testes)"
summary: "npx vitest run src/lib/processoCnj.test.ts com a implementação nova removida (git stash push -- web/src/lib/processoCnj.ts) mas os testes novos presentes: 24 falhas -- 18 por ReferenceError (tribunalDaUrl/validarTribunalCoerente/ArtifactProvenanceError/itemIdDaUrl/validarMetadataDjen/validarMetadataDjenUrls inexistentes), 4 nos dois testes de fonteUrls (assinatura antiga não aceitava `tribunal` na linha, TypeScript aceitava em runtime mas o comportamento não incluía a checagem) e 2 nos testes de integração de buscarProcesso (asserção real falhando -- `expected false to be true` -- confirmando que o comportamento antigo não degradava a fonte djen para os dois cenários de proveniência incoerente). 118 testes pré-existentes continuaram passando (nenhuma regressão introduzida pelos testes novos em si). git stash pop restaurou a implementação em seguida."
---

# Evidência: RED confirmado (24/24 falhas esperadas, motivo certo em cada caso)
