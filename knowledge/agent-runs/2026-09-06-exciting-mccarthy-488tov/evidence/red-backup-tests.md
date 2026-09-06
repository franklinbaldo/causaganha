---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-488tov-evidence-red-backup-tests"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal_id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
kind: "test_red"
reference: "web/src/lib/savedConsultationsBackup.test.ts (before savedConsultationsBackup.ts existed); web/src/components/SavedConsultations.backup.test.ts (before SavedConsultations.svelte had export/import UI)"
summary: "`npx vitest run src/lib/savedConsultationsBackup.test.ts` failed at import resolution ('Failed to resolve import ./savedConsultationsBackup') because the module did not exist yet. `npx vitest run src/components/SavedConsultations.backup.test.ts` failed 7/7 (getByText('Exportar salvos')/getByText('Importar salvos')/input[type=file] all absent) because the component had no export/import UI yet. Both confirmed RED before any production code was written."
---

# Evidência RED

Os dois arquivos de teste (módulo puro e componente) falharam antes da implementação: o primeiro por import não resolvido, o segundo com 7/7 testes falhando por ausência dos botões/input de export/import.
