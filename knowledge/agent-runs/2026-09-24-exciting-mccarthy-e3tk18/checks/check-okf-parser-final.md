---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-e3tk18-check-okf-parser-final"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
summary: "conformant=true, 0 diagnosticos, concept_count=2128 apos a arvore completa deste relatorio (run.md + 4 readings + 1 goal + 1 decision + 2 evidences + 3 checks ate este ponto) ser escrita."
---

# Check: okf-parser sobre o bundle knowledge/ apos escrever o relatorio

Confirma que a arvore OKF desta rodada e conformante com
`okf.schema.sql` antes de rodar a suite completa e o gate de
completude.
