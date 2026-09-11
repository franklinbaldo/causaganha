---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-njkncp-evidence-diff"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
kind: "diff"
reference: "src/causaganha/processos/service.py (+22/-6), tests/causaganha/processos/test_service.py (+22/-1, plus FonteCobertura import)"
summary: "service.py: added _fonte_cobertura(nome, fonte) helper that returns FonteCobertura with status defaulted to 'unknown' and registros defaulted to 0 when the source entry isn't a dict or lacks those keys/types; _carregar_cobertura now guards data/sources not being dicts and calls the helper per source instead of indexing fonte['status']/fonte['rows'] directly. test_service.py: added test_malformed_report_is_partial_not_fatal (writes a report.json with sources.djen missing 'rows', asserts buscar_processo returns encontrado=True with the djen entry defaulted to registros=0 and no false 'indisponível' warning) and imported FonteCobertura from causaganha.processos.models."
---

# Diff desta rodada

`git diff --stat`: `src/causaganha/processos/service.py | 28 +++++++++++++++++++++++-----` e `tests/causaganha/processos/test_service.py | 30 +++++++++++++++++++++++++++++-`. Corrige `_carregar_cobertura` para degradar por-fonte em vez de propagar `KeyError`.
