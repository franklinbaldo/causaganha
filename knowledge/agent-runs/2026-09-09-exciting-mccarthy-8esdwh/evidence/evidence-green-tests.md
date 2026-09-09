---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8esdwh-evidence-green-tests"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
goal_id: "2026-09-09-exciting-mccarthy-8esdwh-goal-csv-manifest-escaping"
kind: "test_green"
reference: "uv run pytest tests/datajud/test_datajud_manifest.py tests/tjro_juris/test_juris_manifest.py tests/stj_acordaos/test_stj_manifest.py -q (post-fix)"
summary: "27 tests passed (24 pre-existing + 3 new), after switching ManifestDataJud.save_local, ManifestJuris.save_local, and ManifestSTJ.save to csv.writer, and ManifestSTJ.load_text's row parsing from line.split(',') to csv.reader. All pre-existing plain-text-format assertions (e.g. stj's lines[1].startswith('a.json,json,2024-02-01,,1,')) stayed green unchanged, confirming csv.writer's default QUOTE_MINIMAL quoting is byte-identical to the old f-string join for comma-free fields."
---

# Evidência GREEN

27 testes passaram (24 pré-existentes + 3 novos) após a correção nos três módulos de manifesto.
