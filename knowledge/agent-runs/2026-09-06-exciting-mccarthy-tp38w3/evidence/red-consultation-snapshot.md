---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-red-consultation-snapshot"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
kind: "test_red"
reference: "web/src/lib/consultationSnapshot.test.ts written before web/src/lib/consultationSnapshot.ts existed; `npx vitest run consultationSnapshot` (web/)"
summary: "With the test file present and the implementation module absent, vitest failed at the import-resolution stage: 'Failed to resolve import \"./consultationSnapshot\" from \"src/lib/consultationSnapshot.test.ts\". Does the file exist?' (0 tests ran, 1 failed suite). This is a genuine RED against non-existent production code, covering buildConsultationSnapshot (present-only fields, indisponibilidade never comparable) and compareConsultationSnapshots (sem_historico, mudou on real field change, mudou on new fonte, sem_mudanca, indisponibilidade never inferred as change, nao_comparavel when every previously-baselined source is unavailable now)."
---

# RED: consultationSnapshot.ts ainda não existe

`npx vitest run consultationSnapshot` falha na resolução do import antes mesmo de rodar os `describe`/`it` — confirma que os 8 casos de teste (build + compare) exercitam um módulo real ainda por implementar, não uma tautologia.
