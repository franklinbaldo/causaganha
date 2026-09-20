---
type: AgentGoal
id: "2026-09-20-exciting-mccarthy-6nbygb-goal-djen-sample-batch25"
run_id: "2026-09-20-exciting-mccarthy-6nbygb"
goal: "Ingerir vigesimo quinto lote real multi-tribunal para o corpus de treino do segmentador (#1050), apos mesclar #1590/#1591"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30/30 em val/test; document_count=184 apos os merges desta rodada, ainda abaixo do piso. Rescan ao vivo mostrou algo novo: TJMG/TJRN/TJRS/TJSE (proximo tier mais baixo, store_count 2-3) estao esgotados para as categorias Sentenca/Acordao -- so tem candidatos 'Decisao' (tipo nunca usado no corpus, sem guideline de tipo estabelecida), mesmo padrao de esgotamento ja documentado para TJSC/TRF6/TRF4. TJBA tem so 1 candidato elegivel e e exatamente o quase-duplicado ja identificado (SequenceMatcher 0.98 vs TJBA/574460085) que a propria PR #1590 reverteu nesta rodada -- nao reusavel. TJMS tem 0 elegiveis. O proximo tier realmente disponivel (store_count=5, Sentenca/Acordao com candidatos amplos) e TJCE/TJMT/TJRJ/TJTO/TRF3/TRF5."
success_signal: "6 documentos novos (1 por tribunal: TJCE, TJMT, TJRJ, TJTO, TRF3, TRF5) anotados por subagentes independentes, fidelidade verbatim verificada byte-a-byte contra o parser real, sem near-duplicate corpus-wide (confirmado via SequenceMatcher contra todo documento ja armazenado do mesmo tribunal, nao so entre os candidatos do lote), ingeridos via scripts/ingest_djen_sample_technique1_batch.py, document_count sobe de 184 para 190, ruff/pytest verdes, PR aberta e mesclada apos CI verde."
status: "in_progress"
---

# Goal: vigesimo quinto lote real multi-tribunal para #1050

Apos mesclar #1590/#1591, o document_count real e 184. Live rescan
(script ad-hoc em `/tmp/scan_batch25.py`, mesma logica de limpeza HTML
do lote 3) do proximo tier mais baixo (TJMG/TJRN/TJRS/TJSE,
store_count 2-3) encontrou zero candidatos Sentenca/Acordao elegiveis
em todos os quatro -- so haveria candidatos do tipo "Decisao"
(interlocutoria), um tipo de documento nunca usado no corpus e sem
guideline de anotacao propria (o prompt canonico so cobre
SENTENCA/ACORDAO). Introduzir um tipo novo sem validacao previa seria
exatamente o tipo de expansao por impulso que o proprio backlog adverte
contra ("nao perseguir uma categoria rara" / nova). TJBA (store_count=4)
tem 1 unico candidato elegivel e e o mesmo quase-duplicado
(574460088, ratio 0.98 vs 574460085) que a PR #1590 acabou de reverter
nesta mesma rodada -- nao reusavel. TJMS tem 0.

Pulei para o proximo tier realmente disponivel: TJCE/TJMT/TJRJ/TJTO/
TRF3/TRF5 (store_count=5, todos com dezenas de candidatos Sentenca
elegiveis). Selecionados 1 por tribunal, tamanho moderado
(~10-15K caracteres), verificados sem near-duplicate entre si E contra
todo documento ja armazenado do mesmo tribunal (nao so entre os
candidatos do proprio lote -- a licao exata da revisao de #1590).
