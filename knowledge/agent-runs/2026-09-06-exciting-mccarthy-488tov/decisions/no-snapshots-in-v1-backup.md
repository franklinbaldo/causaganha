---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-488tov-decision-no-snapshots-in-v1-backup"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal_id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
question: "Should the v1 backup file include the #1133/#1232 comparison snapshots/baselines alongside the SavedConsultation list, or only the list?"
choice: "Only the SavedConsultation list (id/type/cnj-or-params/label/savedAt). Snapshots stay device-local, keyed by consultationSnapshotStore, and are never exported. Importing a process consultation into a new browser starts it at 'sem_historico' (first capture) on its next automatic check, exactly like adding it fresh."
rationale: "Issue #1235 explicitly names this as an open decision and offers the same fallback: 'se isso ampliar demais o slice, exportar primeiro apenas a lista e documentar que a baseline recomeça no novo navegador.' Including snapshots would require exporting the full comparison payload (buildConsultationSnapshot's field set) and deciding how to merge two independent snapshot histories on import — real complexity with no acceptance-criterion actually requiring it (the criteria only require the list round-trips and that #1232's semantics are not silently altered). Restarting the baseline on import changes nothing about #1232's fix (a 'mudou' verdict still requires explicit acknowledgement before the baseline advances) — it just means the first post-import check has no prior baseline to compare against, identical to adding a brand-new consultation. This keeps the v1 format small, testable, and unambiguous, and can be revisited as a v2 schema_version later without breaking v1 files already on users' disks."
---

# Decisão: escopo do backup v1

Backup v1 exporta só a lista de consultas salvas, não os snapshots de comparação. Justificativa e critério de aceite cobertos em `tests/../savedConsultationsBackup.test.ts` (round-trip só sobre `SavedConsultation[]`) e no próprio texto da issue #1235, que antecipa esse trade-off como aceitável.
