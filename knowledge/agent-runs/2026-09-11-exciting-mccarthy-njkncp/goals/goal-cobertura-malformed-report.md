---
type: AgentGoal
id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal: "Make causaganha.processos.service._carregar_cobertura degrade to a partial result (empty cobertura_dataset + the documented 'relatório de cobertura indisponível' aviso) on a syntactically-valid but wrong-shaped indice_processual.report.json, instead of letting KeyError/TypeError escape buscar_processo."
rationale: "service.py's own module docstring and buscar_processo's docstring both promise that failing to load the coverage report is 'parcial ... nunca uma exceção' -- but _carregar_cobertura's list comprehension (fonte['status']/fonte['rows']) sits outside its try/except, which only catches OSError/httpx.HTTPError/json.JSONDecodeError. A report that parses as valid JSON but whose 'sources' entries are missing 'status'/'rows' (or aren't dicts) raises an uncaught KeyError/TypeError that propagates through the MCP tool as an unhandled 500, instead of the documented degradation. The TypeScript twin (web/src/lib/processoCnj.ts::fetchCobertura) already gets this right -- it reads info?.status ?? 'unknown' and Number(info?.rows ?? 0) inside the same try block that guards fetch/JSON failures -- so the two 'same design' implementations have silently diverged, exactly the Python/TS-parity bug class this file's own test_report_fetch_follows_archive_org_redirect regression test documents a prior instance of (#1042)."
success_signal: "A new regression test (test_malformed_report_is_partial_not_fatal) is RED against the current _carregar_cobertura (confirmed: KeyError: 'rows' propagates out of buscar_processo) and GREEN once the fix lands; the full causaganha/processos test suite, ruff check and ruff format --check stay green; a PR is opened and merged."
status: "achieved"
---

# Goal: cobertura report malformed-shape resilience

`_carregar_cobertura` deve degradar (não lançar) quando `indice_processual.report.json` é sintaticamente válido mas tem forma errada (faltando `status`/`rows` em algum `sources[fonte]`), igual ao gêmeo TypeScript `fetchCobertura`.
