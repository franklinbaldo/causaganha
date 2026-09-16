---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-zrek2s-check-okf-parser-after-evidence"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "observed"
evidence_id: null
summary: "conformant=true, concept_count=1829, markdown_count=1832, reserved_count=3, diagnostics=[]"
---

# Check: okf-parser apos as evidencias do lote 7

Rodado apos criar as evidencias de ingestao, do fix de strip()/NBSP e da
verificacao do falso positivo do audit semantico. Bundle `knowledge/`
permanece conformante.
