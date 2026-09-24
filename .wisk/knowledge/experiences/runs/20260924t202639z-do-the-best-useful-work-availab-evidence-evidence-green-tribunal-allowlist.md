---
type: "RunEvidence"
id: "run-evidence/20260924t202639z-do-the-best-useful-work-availab/evidence-green-tribunal-allowlist"
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
kind: "test_green"
reference: "tests/datajud/test_datajud_tribunais.py, tests/causaganha_mcp/test_datajud_facetas.py::test_facetas_rejects_invalid_tribunal_before_network, tests/causaganha_mcp/test_datajud_processo.py::test_processo_estado_rejects_invalid_tribunal_before_network, tests/causaganha_mcp/test_tool_behavior.py::test_datajud_status_rejects_invalid_tribunal_before_network"
summary: "New datajud.tribunais.validar_tribunal() (allowlist sourced from causaganha.config.TRIBUNAIS) is wired into all three tools before any network/service call. All new tests pass; each proves zero network/filesystem call is attempted for an invalid tribunal (route.called is False / a monkeypatched download_file that raises if invoked is never triggered)."
goal: "run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"
---

# RunEvidence
