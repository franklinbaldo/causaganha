---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-1-reconcile-sources"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "diff"
reference: ".github/workflows/update-catalog.yml:104, scripts/reconcile_processos.py:52-109"
summary: "#924 §3.1 claimed juris/datajud never reached the public catalog and RECONCILE_EXPECTED_SOURCES excluded them with a permanent warning. Live on main: `RECONCILE_EXPECTED_SOURCES: djen,juris,stj,datajud` (update-catalog.yml:104), with a code comment reading 'All four now publish real IA items ... see tests/test_update_catalog_workflow.py and issue #924 3.1' — this was already fixed by an earlier round and explicitly cites this issue. reconcile_processos.py's SOURCE_NAMES/_expected_sources()/juris+datajud item discovery (lines 52-109, 279-306) confirm both sources are live inputs to indice_processual.parquet, not stubs."
---

# Evidência — #924 §3.1 (JURIS/DataJud → catálogo) já resolvido

`RECONCILE_EXPECTED_SOURCES` em `main` já inclui `juris,stj,datajud`, com comentário citando esta issue.
