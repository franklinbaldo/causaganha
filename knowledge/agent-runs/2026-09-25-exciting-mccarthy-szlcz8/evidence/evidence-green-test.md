---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-szlcz8-evidence-green-test"
run_id: "2026-09-25-exciting-mccarthy-szlcz8"
goal_id: "2026-09-25-exciting-mccarthy-szlcz8-goal-juris-discovery-allowlist"
kind: "test_green"
reference: "tests/test_reconcile_processos.py (31 testes, arquivo inteiro)"
summary: "Após reescrever _discover_juris_items em scripts/reconcile_processos.py para ler juris_archive.MANIFEST_DOWNLOAD_URL via ManifestJuris.load_text() e derivar os anos confiáveis apenas de janelas ia_status='uploaded' (nunca mais chamando advancedsearch.php), e migrar os ~7 mocks existentes de advancedsearch.php para o manifesto (_mock_juris_remote, test_fetch_juris_from_ia_matches_published_juris_url_encoding, _mock_empty_ia, e 3 mocks inline): uv run pytest -q tests/test_reconcile_processos.py -k TestDiscoverJurisItemsAllowlist -> 5 passed. uv run pytest -q tests/test_reconcile_processos.py (arquivo inteiro) -> 31 passed, sem regressão em nenhum teste existente (fetch_juris_from_ia, ensure_juris_parquets, reconcile completo via TestFullReconcileWithoutLocalParquets, TestUnavailableSources, TestCorruptedParquetHandling, TestLocalSourceUrlProvenanceWarning)."
---

# Evidência: GREEN confirmado (31/31 em test_reconcile_processos.py)
