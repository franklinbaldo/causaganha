---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-50ns70-evidence-live-probe-refresh"
run_id: "2026-09-15-exciting-mccarthy-50ns70"
goal_id: "2026-09-15-exciting-mccarthy-50ns70-goal-cors-probe-ci"
kind: "runtime"
reference: "docs/planning/evidence/archive-cors-probe-real-browser.json, docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json"
summary: "Ran `uv run python -m scripts.benchmarks.archive_cors_probe --chromium-path /opt/pw-browsers/chromium --output docs/planning/evidence/archive-cors-probe-real-browser.json` live against archive.org: metadata_endpoint ok=true/type=cors/63097 bytes; download_endpoint_range_request ok=false/errorName=TypeError/errorMessage='Failed to fetch'; verdict=expected_blocked, passed=true, exit code 0 -- reproduces the exact same real-browser result the prior .mjs-based round recorded, now via the portable Python script. Also re-ran `uv run python -m scripts.benchmarks.pilot_tjro_2026_real_archive_readback --output docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json` (whose docstring/output text referenced the now-deleted .mjs file) to refresh its evidence with updated, accurate prose and a fresh live run: parquet_magic_verified=true, download_endpoint_cors_enabled=false, metadata cors_enabled=true, native cold_query_ms=2363/warm~2-9ms on sample_date 2026-09-01 -- both committed as refreshed evidence."
---

# Evidência: probe ao vivo contra archive.org

Execução real do novo script Python contra o `archive.org` reproduz o mesmo bloqueio de CORS já documentado, agora de forma portátil (sem o caminho hardcoded do sandbox). O script de leitura real do Internet Archive (#1471/#1472) também foi reexecutado para atualizar seu relatório de evidência com o texto revisado.
