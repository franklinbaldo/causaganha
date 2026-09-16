---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-c4y4rc-goal-per-split-floor-diagnosis"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
goal: "Tornar checável e testado, via TDD, o achado de que RFC 0012 Sec 5 item 4 (>=30 val adjudicados, >=30 teste adjudicados) e estruturalmente inatingivel com o corpus atual de 61 documentos, redirecionando o proximo passo real de #1051 para #1050 (crescer o corpus), e corrigir o registro de backlog desatualizado de #1051."
rationale: "10+ rodadas consecutivas desta linhagem escalaram ReviewRecords dentro do pool fixo de 61 documentos (11->31), tratando isso como progresso direto rumo ao piso combinado de RFC 0012 Sec 5.4. O next_move da ultima rodada mesclada (2hb3sq) ja suspeitava que o piso e por split, nao combinado, e pediu verificacao. Verifiquei ao vivo (assign_splits real e uma segunda chamada com evaluation_eligible=train_eligible inteiro, simulando adjudicacao 100%): o teto e val=9/test=9 em ambos os casos, porque val_target/test_target sao proporcionais ao TOTAL de documentos do corpus (61), nao ao pool elegivel. Continuar adjudicando dentro do pool de 61 nunca pode cruzar 30/30 -- e um teto matematico, nao uma questao de mais rodadas. Sem tornar isso um fato testado e publicado, futuras rodadas desta linhagem repetiriam o mesmo padrao (mais um documento, mais um review) indefinidamente sem perceber que o gargalo real mudou de #1051 (adjudicacao) para #1050 (escala do corpus)."
success_signal: "scripts/segmenter_governance_status.py reporta novos campos (val_count/test_count reais via assign_splits e val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication simulando 100% de adjudicacao do corpus atual, mais meets_rfc_0012_split_floor e corpus_scale_blocks_floor) com teste RED antes da mudanca e GREEN depois, incluindo um teste de regressao contra o store real fixando corpus_scale_blocks_floor=True nos valores atuais. Evidencia publicada em docs/planning/evidence/. knowledge/backlog/issue-1051.md atualizado para refletir o estado real (nao mais status: blocked/2026-09-07). Comentario publicado em #1051 e/ou #1050 documentando o achado e redirecionando o next_move da linhagem. uv run pytest tests/segmenter_dataset -q e ruff check/format ficam verdes."
status: "achieved"
---

# Goal: diagnosticar e testar o teto estrutural do piso por split de RFC 0012

Este goal nao adiciona mais um ReviewRecord ao pool de 61 documentos (o
padrao das ultimas 10+ rodadas) -- ele verifica, com evidencia
reproduzivel, se continuar fazendo isso pode sequer atingir a meta, e
corrige o rastro de conhecimento (script de governanca, backlog, issues)
para refletir a resposta.
