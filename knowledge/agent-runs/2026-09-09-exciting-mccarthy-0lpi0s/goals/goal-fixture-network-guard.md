---
type: AgentGoal
id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal: "Make scripts/render_contract_fixture.py fail fast and loudly on any real network access, instead of silently falling through to a live IA download or a swallowed-and-degraded optional-contract warning."
rationale: "The previous round (pf1xhn) hit a real production incident from this exact gap: its own fix to _register_tjro_juris/_register_datajud_capa made them delegate to reconcile_processos.ensure_juris_parquets()/ensure_datajud_parquets(), which read local-file paths from reconcile_processos's own ROOT/DATA_DIR globals -- not renderer.ROOT, the only global the fixture script patched. The frontend integration test silently fell through to a real, slow IA download and timed out at 120s in CI before being caught and fixed by hand. Nothing in the codebase would catch the *next* occurrence of this same class of bug (a new IA-fallback source added to render_queries.py without a matching isolation entry in render_contract_fixture.py) until it, too, causes a slow or flaky CI failure discovered after the fact."
success_signal: "A new regression test proves render_fixture() raises immediately (not: hangs, times out, or silently degrades to a skipped-optional warning) when any source's local fixture input is missing and its registration would otherwise fall through to a real urllib.request.urlopen or httpx.Client network call. The existing web fixture integration test (renderedContracts.integration.test.ts) and the full Python suite stay green, proving the guard does not fire against the current, fully-mocked fixture set."
status: "achieved"
---

# Goal: guarda de rede real no fixture de contratos

Converter qualquer futuro vazamento de rede real dentro de `render_contract_fixture.py` (a mesma classe de bug que a rodada anterior corrigiu manualmente após um timeout de 120s em CI) numa falha imediata e clara, em vez de um download lento silencioso ou um aviso de "contrato opcional pulado".
