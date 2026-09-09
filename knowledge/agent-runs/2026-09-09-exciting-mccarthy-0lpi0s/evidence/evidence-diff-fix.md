---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-diff-fix"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "diff"
reference: "scripts/render_contract_fixture.py (+ tests/test_render_contract_fixture.py, new file)"
summary: "scripts/render_contract_fixture.py: added RealNetworkAccessError, _patched_attrs() (a save-and-restore context manager for arbitrary (obj, attr, value) triples), and _block_real_network() (patches urllib.request.urlopen and httpx.Client.send to raise RealNetworkAccessError). render_fixture() now builds one patches tuple covering renderer.ROOT/LOCAL_MANIFEST_PARQUET/DEV_RATINGS_DIR/_STJ_PARQUET/_register_comunicacoes and reconcile_processos.ensure_juris_parquets/ensure_datajud_parquets, and applies it plus the network guard via `with _patched_attrs(*patches), _block_real_network():` around the sole renderer.render_all() call -- replacing 7 bare, unrestored module-attribute reassignments. tests/test_render_contract_fixture.py (new, 6 tests) covers the guard directly, the fast-failure-on-missing-input regression, the pre-existing end-to-end render, and the no-state-leak regression."
---

# Evidência: diff da correção

`scripts/render_contract_fixture.py` ganhou uma guarda de rede (`_block_real_network`) e um mecanismo único de patch/restore (`_patched_attrs`), substituindo 7 reatribuições diretas sem restauração por um único `with`. Novo arquivo de testes cobrindo os seis comportamentos relevantes.
