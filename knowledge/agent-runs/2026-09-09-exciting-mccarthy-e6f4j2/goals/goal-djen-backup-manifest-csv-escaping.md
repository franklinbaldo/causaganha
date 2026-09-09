---
type: AgentGoal
id: "2026-09-09-exciting-mccarthy-e6f4j2-goal-djen-backup-manifest-csv-escaping"
run_id: "2026-09-09-exciting-mccarthy-e6f4j2"
goal: "Make SyncManifest.to_csv()/load_from_csv()/apply_segment_csv() in src/djen_backup/manifest.py round-trip a field value containing a comma without silent corruption, by switching from raw f-string comma-joining and str.split(',') to csv.writer/csv.reader, mirroring the fix already landed today in src/datajud/manifest.py, src/tjro_juris/manifest.py and src/stj_acordaos/manifest.py."
rationale: "SyncManifest is the canonical sync engine's own persistence layer (local disk cache via save_to_disk/load_from_disk, and the append-only manifest-log segment format via apply_segment_csv, consumed by scripts/render_manifest_parquet.py's compactor). Its to_csv/load_from_csv/apply_segment_csv share the exact unescaped-CSV bug shape the immediately preceding round (8esdwh) just fixed in three sibling manifest modules, and that round's own next_move explicitly asked for this module to be checked next. Every current field writer (engine.py's _classify_djen_status, published.py, service.py) only ever produces short enum tokens or ISO timestamps, so this is a real but currently-latent format-contract bug -- not yet triggered by live data -- exactly like every fix in this family today, closing out the one manifest module the prior round's search scope explicitly skipped."
success_signal: "A new regression test proves a comma-bearing field (e.g. a hypothetical djen_raw value with an embedded comma) silently corrupts on the current to_csv/load_from_csv and apply_segment_csv round-trip -- RED before the fix -- and round-trips exactly after switching both to the csv module -- GREEN after. All pre-existing tests in tests/djen_backup/{test_ia_contract,test_segments,test_manifest_counts,test_published_manifest}.py stay green unchanged (proving csv.writer's default quoting is byte-identical to the old f-string join for comma-free fields, the same invariant 8esdwh's fix already established for its three sibling modules). Full Python suite, ruff check, ruff format --check, and uvx vulture stay green, and a PR is opened, driven to green CI, and merged."
status: "achieved"
---

# Goal: escapar CSV do SyncManifest canônico (djen_backup)

Fechar, no módulo canônico `src/djen_backup/manifest.py`, o mesmo buraco de escaping de CSV que a rodada anterior (8esdwh) já corrigiu em três módulos de manifesto irmãos.
