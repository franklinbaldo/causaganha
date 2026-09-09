---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-02ggxp-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-02ggxp"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Same correctness rules as the last several same-day rounds: djen_raw is the raw DJEN HTTP transport code, never a verdict on availability; a bare HTTP 200 is not 'available' unless the body also carries a download URL, else it is 'Sem comunicacoes' (absent, same as 404/400); 403 must never be treated as absent (CloudFront/WAF rate-limiting); sync-manifest.parquet is the sole source of truth, sync-manifest.csv is a derived export only. 'What NOT to do' list unchanged: no boto3 for IA uploads, keep the per-item lock in archive.py, never mark_djen_raw with a derived category, never generate cache JSONs from non-manifest sources, no broad except Exception outside the ADR-0011 worker-pool bulkhead pattern. File map matches the current tree. No drift found between CLAUDE.md and the current codebase."
---

# Leitura de CLAUDE.md

Releitura completa no inicio da rodada. Nenhuma divergencia encontrada entre as regras documentadas e o estado atual do codigo.
