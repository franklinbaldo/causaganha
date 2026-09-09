---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8esdwh-evidence-red-tests"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
goal_id: "2026-09-09-exciting-mccarthy-8esdwh-goal-csv-manifest-escaping"
kind: "test_red"
reference: "uv run pytest tests/datajud/test_datajud_manifest.py tests/tjro_juris/test_juris_manifest.py tests/stj_acordaos/test_stj_manifest.py -q -k comma (pre-fix)"
summary: "All three new comma round-trip tests failed before the fix, exactly as predicted: datajud's test_roundtrip_preserves_a_comma_in_status silently got back status='erro' instead of 'erro, timeout' (DictReader's overflow discarded); tjro_juris's test_roundtrip_preserves_a_comma_in_ia_status raised ManifestFormatError (invalid literal for int() with base 10: ' retry pending') because the shifted column landed in n_docs; stj_acordaos's test_roundtrip_preserves_a_comma_in_arquivo got back arquivo='acordaos' instead of 'acordaos, 2024.zip' (naive line.split(',') truncation). Confirms the bug is real (silent corruption or a crash, not just a hypothetical), even though no current call site triggers it in production."
---

# Evidência RED

As três novas asserções de round-trip com vírgula falharam antes da correção, cada uma de um jeito diferente: truncamento silencioso, exceção por coluna deslocada, e truncamento silencioso novamente.
