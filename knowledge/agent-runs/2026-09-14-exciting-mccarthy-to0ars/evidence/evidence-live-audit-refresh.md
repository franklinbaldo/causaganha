---
type: AgentEvidence
id: "2026-09-14-exciting-mccarthy-to0ars-evidence-live-audit-refresh"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
kind: "runtime"
reference: "docs/planning/evidence/audit-cnj-parquets-2026-09-14.json (refreshed); uv run python scripts/audit_cnj_parquets.py --output ..."
summary: "Re-ran the audit (read-only, real archive.org catalog, no re-upload) with the new value-verification path wired in. All 24 files audited again in ~3.5 minutes. Result: reorder_candidate=15 (unchanged from before this round), national_index=1 (unchanged), and all 8 files that were stuck in verify_values before this round (djen-cjf-2021, djen-tjam-2021, djen-tjap-2021, djen-tjdft-2021 x comunicacoes+processos) are now verified_unsorted -- a real adjacent-row inversion was found reading their actual numero_processo values in physical file order, via read_value_order. Zero files remain in verify_values or resolve to verified_sorted in this live run: every previously-inconclusive file is a genuine reorder candidate, none was a false positive that footer stats alone happened to miss. This directly extends #1471/#1472's eventual rollout list from 15 to 23 real reorder candidates (the 8 newly-confirmed files plus the pre-existing 15), removing the ambiguity the issue's own acceptance criteria flagged. Refreshed docs/planning/evidence/audit-cnj-parquets-2026-09-14.json in place (same day, same report this round's own HEAD commit 94c180b introduced via PR #1486) rather than adding a second same-day file, since this is a strict refinement of the same day's audit, not a new audit run on a different day."
---

# Runtime: auditoria ao vivo com verificação real de valores

Re-execução completa contra o catálogo real do archive.org (somente leitura). Os 8 arquivos antes presos em `verify_values` agora são `verified_unsorted` -- inversão real confirmada lendo os valores físicos de `numero_processo`. Nenhum arquivo permanece em `verify_values`; nenhum se revelou já ordenado. Lista de candidatos a reordenação para #1471/#1472 passa de 15 para 23 arquivos reais. `docs/planning/evidence/audit-cnj-parquets-2026-09-14.json` atualizado no lugar.
