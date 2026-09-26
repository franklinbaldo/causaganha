---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-p08457-reading-okf"
run_id: "2026-09-26-exciting-mccarthy-p08457"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-26-exciting-mccarthy-ku8qje/run.md (AgentRun mais recente), .wisk/knowledge/experiences/handoffs/handoff-issue-1051-adjudication-continuation.md (handoff do loop Wisk paralelo), knowledge/backlog/issue-1050.md, knowledge/backlog/issue-950.md"
finding: "O AgentRun mais recente (ku8qje) fechou o Lote 28 de #1050 (document_count 195->197), cruzando o teto de escala de corpus de RFC 0012 Sec 5 item 4 (`corpus_scale_blocks_floor` True->False) -- confirmado ainda válido ao vivo nesta rodada. Seu `next_move` aponta explicitamente #1051 (adjudicar mais documentos) como o próximo avanço natural, priorizando candidatos que caiam no split de TEST (`test_count` real=2 de um teto de 30, muito atrás de `val_count`=30 já no teto). O handoff paralelo do loop Wisk (`handoff-issue-1051-adjudication-continuation.md`) documenta a mecânica de trabalho reutilizável: `scripts/annotate_second_independent.py` (segunda anotação independente, exige `model_family` distinto do da primeira -- convenção observada no diff de PR #1665: `prompt_subagents:haiku` via Agent tool com `model=haiku`) + `scripts/adjudicate_segmenter_review.py` (reconcilia em um `ReviewRecord` aceito) + `scripts/segmenter_governance_status.py` (contagens reais vs. teto). Também documenta duas armadilhas: (1) um documento cuja única anotação existente tem `seeded_with != 'none'` nunca pode ser adjudicado -- filtrar candidatos por isso antes de escolher; (2) `assign_splits` é recomputado do zero a cada chamada a partir de uma ordem de hash fixa por `(seed, group_id)` -- qual documento cai em val vs. test não é escolhível diretamente por identidade, só simulável (`assign_splits` com o candidato adicionado a `evaluation_eligible` antes de gastar esforço de anotação nele). Simulação ao vivo desta rodada (script ad-hoc, ver decision) confirma 134 dos 141 candidatos elegíveis (anotação única, `seeded_with=='none'`, sem review) aumentariam `test_count` se adjudicados isoladamente -- a maioria do pool serve o objetivo. `knowledge/backlog/issue-1050.md` (27+1 lotes documentados) e `issue-950.md` seguem atualizados e consistentes com o estado real; nenhum `knowledge/backlog/issue-1051.md` existe ainda apesar de duas rodadas anteriores terem notado a lacuna -- candidato a ser criado por esta rodada, já que agora há histórico real de adjudicação (1 review da rodada ns7mbo/#1665, mais o trabalho desta rodada) para documentar."
---

# Leitura: conhecimento OKF relevante

Revisado o `AgentRun` mais recente (ku8qje) e o handoff paralelo do
loop Wisk sobre #1051. Confirmado ao vivo: o teto de corpus (30/30) já
foi cruzado; o gargalo real agora é cobertura de adjudicação do lado
TEST (`test_count=2` de 30). A mecânica reutilizável
(`annotate_second_independent.py` + `adjudicate_segmenter_review.py` +
`segmenter_governance_status.py`, com `model_family` distinto via
Agent tool `model=haiku`) é seguida por esta rodada. Simulação ao vivo
confirma que a maioria do pool elegível avança `test_count` se
adjudicado. `knowledge/backlog/issue-1051.md` ainda não existe --
criado por esta rodada, já que agora há histórico real para registrar.
