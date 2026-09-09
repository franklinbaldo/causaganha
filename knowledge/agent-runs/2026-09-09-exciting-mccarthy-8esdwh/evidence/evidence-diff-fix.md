---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8esdwh-evidence-diff-fix"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
goal_id: "2026-09-09-exciting-mccarthy-8esdwh-goal-csv-manifest-escaping"
kind: "diff"
reference: "git diff src/datajud/manifest.py src/tjro_juris/manifest.py src/stj_acordaos/manifest.py"
summary: "3 files changed, 21 insertions(+), 16 deletions(-). datajud/manifest.py and tjro_juris/manifest.py: save_local now builds an io.StringIO buffer through csv.writer(lineterminator='\\n') instead of an f-string-joined line per entry, writing the header and each row via writer.writerow(). stj_acordaos/manifest.py: added `import csv`/`import io`; save() rewritten the same way; load_text()'s per-line parsing switched from `line.split(',')` to `next(csv.reader([line]))`, a minimal change that preserves every other line of existing header-detection, blank-line-skip, and malformed-row-count logic untouched."
---

# Evidência: diff da correção

Três arquivos, mudança pequena e simétrica: escrita via `csv.writer`, leitura de `stj_acordaos` via `csv.reader` por linha (mantendo o resto da lógica existente intacto).
