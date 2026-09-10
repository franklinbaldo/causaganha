---
type: AgentGoal
id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal: "scripts/render_manifest_parquet.py's write_back_csv() must derive the absent/200 self-consistency rewrite from djen_backup.absent_consistency's constants (ABSENT, BARE_200_RAW, PREFIXED_200_RAW_PREFIX, NO_PUBLICATIONS_SENTINEL), which are already imported at the top of the same file and already used correctly by _normalize_manifest a few lines above -- instead of re-typing the same literal strings a second time."
rationale: "src/djen_backup/absent_consistency.py exists specifically because PR #1323 caught two independent runtimes (SyncManifest._normalize_event and render_manifest_parquet.py's _normalize_manifest) re-typing the same 'absent status with a contradictory 200 raw' literals and drifting apart. Its docstring is explicit: 'the SQL literals below must be interpolated from these same constants rather than re-typed.' _normalize_manifest interpolates them correctly, but write_back_csv, in the same file, re-types the identical contract as bare string literals ('absent', '200', '200:', 'no_publications') inside an ibis.cases() expression. tests/test_render_manifest_writeback.py proves write_back_csv runs standalone (without _normalize_manifest first) in a real path, so this is not dead code -- it is a live, unfixed second copy of exactly the bug class PR #1323 already paid to discover once, sitting in the very file whose docstring warns against it."
success_signal: "A new test in tests/test_render_manifest_writeback.py monkeypatches the render_manifest_parquet module's imported constant names (ABSENT, BARE_200_RAW, PREFIXED_200_RAW_PREFIX, NO_PUBLICATIONS_SENTINEL) to distinct sentinel values and asserts write_back_csv's CSV output actually reflects the patched values -- proving the function derives its behavior from the imported constants rather than from re-typed literals. This test fails RED against the current write_back_csv (which ignores the patched module attributes because it never references them) and passes GREEN once write_back_csv is rewritten to reference the constants instead of the literals. The existing test_write_back_makes_absent_200_rows_self_consistent stays green unmodified since the constants' actual values are unchanged. Full uv run pytest -q, ruff check, ruff format --check all stay clean."
status: "achieved"
---

# Goal: eliminate the second re-typed copy of the absent/200 self-consistency contract

`write_back_csv` em `scripts/render_manifest_parquet.py` reescrevia à mão o mesmo
contrato `djen_status == "absent"` / `djen_raw == "200"` / prefixo `"200:"` /
sentinela `"no_publications"` que `_normalize_manifest` (mesmo arquivo) já deriva
corretamente das constantes de `djen_backup.absent_consistency` -- constantes já
importadas no topo deste mesmo módulo. Corrigida a duplicação e adicionado um
teste de regressão que a teria capturado.
