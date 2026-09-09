---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-e6f4j2-evidence-red-tests"
run_id: "2026-09-09-exciting-mccarthy-e6f4j2"
goal_id: "2026-09-09-exciting-mccarthy-e6f4j2-goal-djen-backup-manifest-csv-escaping"
kind: "test_red"
reference: "tests/djen_backup/test_ia_contract.py::test_manifest_csv_round_trip_preserves_comma_in_field; tests/djen_backup/test_segments.py::test_format_event_and_apply_segment_csv_preserve_comma_in_djen_raw; tests/djen_backup/test_segments.py::test_to_segment_csv_round_trips_comma_in_djen_raw"
summary: "Wrote three new tests, each proving a comma-bearing djen_raw value silently corrupts the current hand-rolled CSV round-trip. Verified RED by stashing the src/djen_backup/{manifest,segments}.py fix (git stash push on only those two files) and running the three tests against unmodified main: all three failed with the exact corruption predicted -- 'network,timeout' read back as bare 'network' with the trailing ',timeout' silently swallowed (either dropped entirely via apply_event's field routing, or clobbering the neighboring updated_at column depending on the path). Then git stash pop restored the fix and reran (see evidence-green-tests). This mirrors the exact TDD shape of every fix in this AgentRun family today."
---

# RED: comma silently corrompe djen_raw no round-trip atual

Três testes novos provam que um valor de `djen_raw` com vírgula é corrompido silenciosamente pelo formato CSV artesanal atual (`f"{a},{b},..."` na escrita, `str.split(",")` na leitura). Confirmado RED isolando o fix via `git stash` e rodando contra o código anterior.
