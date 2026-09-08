---
type: AgentDecision
id: "2026-09-08-exciting-mccarthy-b4t8pv-decision-confirmed-in-pending-filter"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
goal_id: "2026-09-08-exciting-mccarthy-b4t8pv-goal-confirmed-pending-undercount"
question: "Should totals.qmd/tribunal_coverage.qmd's pending filter widen to include djen_status='confirmed', or should render_manifest_parquet.py instead normalize 'confirmed' -> 'available' in the parquet itself (like write_back_csv already does for the CSV export)?"
choice: "Widen the .qmd pending filters to `djen_status IN ('available', 'confirmed')`, matching the exact pattern already used by render_manifest_parquet.py's own _print_merge_stats (line 487). Did not touch _normalize_manifest or the parquet write path."
rationale: "'confirmed' is deliberately preserved as a distinct value in the canonical parquet -- src/djen_backup/drain.py:70-74 reads it back specifically to prioritise confirmed-but-unuploaded pairs over merely-available ones (CASE WHEN djen_status = 'confirmed' THEN 0 ELSE 1 END). Normalizing it away to 'available' in the parquet itself, the way write_back_csv does only for the legacy CSV export, would destroy that prioritisation signal for drain.py -- a live runtime consumer -- to fix a reporting-layer display bug. The .qmd files are read-only reporting views over the same parquet every other runtime consumer already reads; widening their own filter to match the vocabulary the parquet actually contains is the same shape as the precedent this repo already established for a structurally identical bug (the prior round's fix to totals.qmd/tribunal_coverage.qmd/court_reliability.qmd's absent filter missing an `ia_status != uploaded` guard, see knowledge/agent-runs/2026-09-08-exciting-mccarthy-izm703/decisions/). Reporting queries should adapt to the runtime's real vocabulary, not the other way around."
---

# Decisao: alargar o filtro de pending nos `.qmd`, não normalizar o parquet

Ver `run.md`/`goals/goal-confirmed-pending-undercount.md` para o contexto do bug corrigido. Mesmo padrao decisorio da rodada `izm703` (guard de reporting, não mudança no runtime que grava o parquet).
