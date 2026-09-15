---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-6kxfkh-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Mesmo piso confirmado por toda a linhagem de rodadas de hoje: guia cobre backend Python (src/causaganha, src/djen_backup), motor djen-backup (ADR 0012, sync-manifest.parquet como fonte de verdade, djen_raw != veredito de disponibilidade), contratos de query .qmd, fronteira CSS Panda vs. bridge index.css, e regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401, pre-commit = ruff check + ruff format --check + pytest -q). Nada mudou no arquivo. Nenhuma secao trata do segmentador/RFC 0012 -- essa governanca vive em docs/rfc/0012 e src/segmenter_dataset/ -- mas o piso de pre-commit vale para qualquer artefato tocado nesta rodada, incluindo data/segmenter_splits/technique1_annotation_prompt.md, scripts/annotate_second_independent.py e scripts/adjudicate_segmenter_review.py."
---

# Leitura: CLAUDE.md

Lido integralmente do system prompt desta sessao. Confirma o mesmo piso ja
registrado por toda a linhagem de rodadas de hoje (yz281l, rt6d4o, cdee4f,
6d5vnd, wvzu11, 5crg57, virf8r, 7drjlg, 2jz691, 2cjjig, b3xdwp, f3feqb,
afj2il, q4zn8q, pxa8pi): nada mudou no arquivo desde a ultima leitura. O
comando de pre-commit (`uv run ruff check && uv run ruff format --check &&
uv run pytest -q`) e a proibicao de `except Exception` amplo fora do
bulkhead do ADR 0011 valem para qualquer artefato tocado nesta rodada.
