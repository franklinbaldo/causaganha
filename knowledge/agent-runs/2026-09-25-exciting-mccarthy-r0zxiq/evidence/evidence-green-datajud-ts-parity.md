---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-green-datajud-ts-parity"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
kind: "test_green"
reference: "web/src/lib/processoCnj.test.ts -- 'datajudItemIdDaUrl / validarMetadataDatajud' e 'validarMetadataDatajudUrls' (10 testes novos, mirroring exato dos describes de juris)"
summary: "`npx vitest run src/lib/processoCnj.test.ts` (em web/) -- 168/168 testes passaram (verde), incluindo os 10 novos para o espelho TS de datajud: extração de item_id, aceitação/rejeição de schema_version e item_id, e o comportamento non-fatal-per-artifact de `validarMetadataDatajudUrls` (URL coerente mantida, URL incoerente descartada com aviso, falha de leitura descartada com aviso, URL não particionada mantida sem tentar ler o rodapé). `web/src/lib/processoCnj.ts::buscarProcesso` agora chama `validarMetadataDatajudUrls` antes de `buildDatajudSql`, mesma posição que `validarMetadataDjenUrls`/`validarMetadataJurisUrls` já ocupavam para as outras fontes."
---

# GREEN: read-side datajud KV_METADATA (TypeScript)

`npx vitest run src/lib/processoCnj.test.ts` — 168/168 verde, incluindo os
10 testes novos que mirroram exatamente os describes já existentes para
juris. `buscarProcesso` agora valida o rodapé de `datajud` na mesma
posição do pipeline que já valida djen/juris.
