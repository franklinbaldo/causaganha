---
type: "RunEvidence"
id: "run-evidence/20260924t202639z-do-the-best-useful-work-availab/evidence-red-tribunal-injection"
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
kind: "test_red"
reference: "tests/causaganha_mcp/test_datajud_processo.py::test_processo_estado_rejects_invalid_tribunal_before_network (pre-fix run)"
summary: "Before the fix, calling processo_estado(cnj=CNJ, tribunal='../tjro') actually issued POST https://api-publica.datajud.cnj.jus.br/api_publica_../tjro/_search (caught by respx as an unmocked request), and datajud_status(tribunal='../tjro') called archive.download_file with file_name='datajud-state-../tjro.zip' -- proving the path-injection threat issue #1615 describes is real, not theoretical."
goal: "run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"
---

# RunEvidence
