---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-ku8qje-decision-1050-over-1051"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
question: "PR #1665 (mesclada por esta rodada) deixou um handoff recomendando continuar adjudicando documentos de #1051 (val/test review). Esta rodada deveria seguir essa recomendação diretamente, ou priorizar #1050 (crescer o corpus)?"
choice: "Priorizar #1050 (2 novos documentos train-only) em vez de continuar a adjudicação de #1051 nesta rodada."
rationale: "`scripts/segmenter_governance_status.py` executado ao vivo no início desta rodada mostra `val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication` = 29/29 -- ou seja, mesmo adjudicando TODOS os documentos train-eligible restantes do pool atual, o teto real não passaria de 29, um documento abaixo do piso RFC 0012 Sec 5 item 4 (>=30/>=30). Qualquer adjudicação adicional nesta rodada teria valor de dataset (mais ReviewRecords accepted), mas não avançaria a métrica que efetivamente bloqueia o RFC -- o teto em si. #1050 é a única alavanca capaz de mover esse teto. O próprio handoff de #1665 reconhece essa dependência ('#1050 train-only ingestion batches still need to push document_count from 195 to >=197 so the ceiling itself can reach 30/30 at all -- adjudication alone cannot cross the floor without that'), então esta decisão não contradiz a recomendação do handoff -- prioriza a pré-condição que o próprio handoff identifica como necessária antes que continuar #1051 volte a ter efeito mensurável no piso."
---

# Decisão: priorizar #1050 (crescer corpus) sobre continuar #1051 (adjudicar)

O teto real de val/test do corpus atual é 29/29, um documento abaixo
do piso RFC 0012 (>=30/>=30), mesmo com 100% de adjudicação do pool
existente. Adjudicar mais documentos de #1051 não teria efeito
mensurável nesse piso até o corpus crescer. Por isso, esta rodada
prioriza `#1050` (2 documentos novos, train-only) sobre continuar a
adjudicação recomendada pelo handoff de #1665 -- que, aliás, reconhece
a mesma dependência.
