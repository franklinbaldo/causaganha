---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qnpypw-check-processo-consultar-live"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
goal_id: "2026-09-05-exciting-mccarthy-qnpypw-goal-close-1042-catalog-parity-proof"
command: "uv run python -c 'from causaganha.processos.service import buscar_processo; buscar_processo(\"0000001-66.2018.8.22.0001\", incluir_documentos=True, limite_documentos=10)'"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-qnpypw-evidence-processo-consultar-live"
summary: "Live call against the published IA artifact returned fontes_presentes=[datajud, djen, juris] with fully populated per-source detail, no fixture/fallback involved."
---

# Check: `processo_consultar` ao vivo
