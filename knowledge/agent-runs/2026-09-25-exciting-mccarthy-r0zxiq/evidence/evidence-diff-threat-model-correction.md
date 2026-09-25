---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-diff-threat-model-correction"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
kind: "diff"
reference: "docs/SECURITY_THREAT_MODEL.md, linha da tabela TM-04"
summary: "A célula 'Estado atual' de TM-04 foi corrigida: a frase anterior ('stj/datajud continuam sem emitir esse rodapé... porque stj_acordaos não tem pipeline') estava factualmente errada para `datajud` (que tem `datajud.archive._write_parquet` sob controle deste repo) -- só era verdadeira para `stj`. Reescrita para descrever o fechamento write+read de datajud (Python+TS) e manter só `stj` como pendência genuína, com a razão correta (sem pipeline de export). A célula 'Gate automatizado' também foi atualizada citando os testes novos de footer e de degradação/aceitação para datajud, e a lista de pendências foi reduzida de 'stj/datajud' para só 'stj'."
---

# Diff: correção da tabela TM-04

`docs/SECURITY_THREAT_MODEL.md` TM-04 corrigido para refletir o estado
real do repositório -- a afirmação anterior de que `datajud` não tinha
pipeline de export sob controle deste repo era falsa (só valia para
`stj`), e a rodada corrigiu o texto junto com o fechamento do gap.
