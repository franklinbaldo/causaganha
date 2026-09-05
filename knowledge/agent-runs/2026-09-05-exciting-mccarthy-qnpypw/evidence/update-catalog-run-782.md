---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-update-catalog-run-782"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
kind: "ci"
reference: "https://github.com/franklinbaldo/causaganha/actions/runs/33970870760 (Update Catalog run #782, job 'Generate & Upload Catalog', head 59f060625af9f766730fbb2e338f63b2804042af, 2026-09-05T14:39-15:10Z)"
summary: "Real, unmodified (not triggered by this session) post-#1040/#1043 run of update-catalog.yml on main. 'Generate reconstructible catalog' succeeded via `uv run ia upload causaganha-catalog`. 'Reconcile processos (DJEN x JURIS x STJ x DataJud)' completed (14:50:56-15:08:47, ~18min, within #1043's 45min timeout), not skipped. Job log shows: djen=5,539,302 processos, juris=1,221,387 (1051 tjro-juris-* parquets), stj=0 (documented structural limitation, #1045), datajud=64; 6,758,093 unified processos, 2,659 in 2+ sources. indice_processual.parquet (248,975,590 bytes) and indice_processual.report.json both confirmed 'uploaded' in the log, to IA item causaganha-dashboard."
---

# Evidência — run real de update-catalog.yml pós-#1040/#1043

Log completo baixado e inspecionado (`get_job_logs` + fetch do blob assinado). Confirma pipeline íntegro: catálogo gerado, upload via `uv`, reconciliação concluída, JURIS/DataJud contribuindo, artefato público publicado com contagens e timestamp reais.
