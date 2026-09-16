---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-hv2ep2-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "No policy change since the last round in this lineage: djen-backup rules (sync-manifest.parquet as sole source of truth, djen_raw is a transport code not a verdict, 403 != absent), the Panda/CSS token boundary (three legacy Svelte islands keep --papel-*/--s-* aliases), and the style rules (ruff strict, TRY300/301/401, no broad except Exception outside the ADR 0011 bulkhead) all still apply. None of it touches src/segmenter_dataset/scripts/ingest_djen_sample_technique1_batch.py directly, but the style rules apply to any new script/test code written this round (e.g. the offset-based tagger helper stayed in the scratchpad, not the repo, precisely to avoid needing to justify it against these rules)."
---

# Leitura: CLAUDE.md

Reconfirmado o guia do projeto na íntegra. Nenhuma mudança de política
desde a última leitura conhecida desta linhagem. As regras de estilo
(ruff estrito, TRY300/301/401, proibição de `except Exception` amplo fora
do bulkhead documentado ADR 0011) se aplicam a qualquer código novo desta
rodada — `tests/segmenter_dataset/test_segmenter_governance_status.py` e
`tests/segmenter_dataset/test_segmenter_audit_scripts.py` foram os únicos
arquivos de produção/teste tocados, e ambos passam `ruff check`/`ruff
format --check` sem exceções.
