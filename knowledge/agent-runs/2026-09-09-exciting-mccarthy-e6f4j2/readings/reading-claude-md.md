---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-e6f4j2-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-e6f4j2"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Key correctness rules unchanged from the last several same-day rounds: djen_raw is the raw DJEN HTTP transport code ('200','404','400','403','timeout','network', or str(status_code)), never a verdict on availability; a bare HTTP 200 is not 'available' unless the body also carries a download URL, else it's 'Sem comunicações' (absent, same as 404/400); 403 must never be treated as absent (CloudFront/WAF rate-limiting); sync-manifest.parquet is the sole source of truth, sync-manifest.csv is retired as a canonical source (derived export only). Explicit 'What NOT to do' list still bans boto3 for IA uploads, removing the per-item lock in archive.py, mark_djen_raw with a derived category instead of the raw code, generating cache JSONs from non-manifest sources, and broad except Exception outside the ADR-0011 worker-pool bulkhead pattern. File map (engine.py/manifest.py/djen.py/archive.py/retry.py/__main__.py, scripts/render_queries.py) matches the current tree. No drift found between CLAUDE.md and the current codebase."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma divergência encontrada entre as regras documentadas e o estado atual do código.
