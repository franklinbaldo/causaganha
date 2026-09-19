---
type: AgentCheck
id: "2026-09-19-exciting-mccarthy-gbf44b-check-okf-parser-caught-yaml-defect"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "failed"
evidence_id: null
summary: "okf-parser flagged OKF001 invalid YAML frontmatter in knowledge/backlog/issue-1050.md after my own batch22 backlog edit: an Edit call had landed unescaped literal quotes inside the unblock_condition double-quoted YAML scalar (a tool mix-up mid-session, not a pre-existing defect). Diagnosed the exact byte range with PyYAML directly, escaped the offending quotes, re-verified conformant."
---

# Check: okf-parser pegou um defeito real de YAML introduzido nesta rodada

Ao editar `knowledge/backlog/issue-1050.md` para registrar o lote 22,
uma chamada de Edit acabou inserindo o texto do lote 22 em
`unblock_condition` (nao em `blocking_reason`, como pretendido) com
aspas literais nao escapadas dentro do escalar YAML entre aspas duplas
-- um erro mecanico da propria sessao, nao um defeito pre-existente no
arquivo. `okf-parser check` detectou corretamente
(`OKF001: invalid YAML frontmatter... while scanning an anchor`).

Diagnostico: a mensagem de erro do `okf-parser` apontava para uma
coluna que nao correspondia diretamente ao offset de caracteres do
Python (provavel diferenca de contagem interna do parser Rust/YAML).
Usei `yaml.safe_load` diretamente sobre cada linha da frontmatter
isoladamente para isolar exatamente qual campo (`unblock_condition`,
nao `blocking_reason`) continha o problema, depois escrevi um scanner
que percorre o valor caractere a caractere contando barras invertidas
precedentes para achar cada aspas duplas nao escapada. Corrigi
escapando todas as aspas dentro do trecho do lote 22 nesse campo, e
reconfirmei com `yaml.safe_load` isolado e depois com o `okf-parser`
completo: `conformant: true`, 0 diagnosticos.
