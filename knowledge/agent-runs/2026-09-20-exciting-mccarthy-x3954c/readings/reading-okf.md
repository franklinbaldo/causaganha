---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-x3954c-reading-okf"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-19-exciting-mccarthy-gbf44b/run.md, knowledge/agent-runs/2026-09-20-exciting-mccarthy-fv62kx/run.md, knowledge/backlog/issue-1050.md, git log de commits wisk(run)/feat(segmenter) ate ad49efc"
finding: "25 lotes reais de #1050 ja mesclados (document_count 61->191, annotation_count ate 244), val_ceiling/test_ceiling em 29/29, ainda abaixo do piso RFC 0012 Sec 5 item 4 (>=30 cada). Todas as rodadas recentes confirmam `scripts/segmenter_governance_status.py` 'ao vivo' antes/depois de cada lote como pratica padrao, sempre relatado como instantaneo -- ate esta rodada, em que ele ficou travado por >8 minutos de CPU a 99.9% num corpus de 191 documentos. Isso e uma regressao de desempenho nao documentada em nenhum relatorio anterior: o proprio codigo de `find_near_duplicates` (dedup.py) ja avisava em docstring 'nao destinado a comparacao all-pairs em escala de corpus', mas `splits.build_groups` o chama exatamente assim (sobre o store inteiro, nao um lote), um descompasso entre a documentacao da funcao e seu uso real que so se tornou custoso o suficiente para notar quando o corpus passou de ~150 documentos."
---

# Leitura: conhecimento OKF relevante

Revisados os dois `AgentRun` mais recentes antes desta sessao
(2026-09-19-gbf44b, batch22; 2026-09-20-fv62kx, batch24) e o historico
de commits ate `ad49efc` (fechamento do batch25/#1594 e da auditoria
#1470/#1595). Padrao estabelecido ao longo de ~25 rodadas: escanear
`data/segmenter_samples/*.jsonl`, selecionar ~6 candidatos reais de
tribunais com `store_count` mais baixo, anotar via subagentes com o
prompt Technique 1, verificar fidelidade verbatim, ingerir via
`scripts/ingest_djen_sample_technique1_batch.py`, e confirmar
`scripts/segmenter_governance_status.py` antes/depois -- sempre descrito
como uma chamada rapida e "ao vivo" nos relatorios anteriores (nenhum
menciona tempo de execucao ou lentidao).

`knowledge/backlog/issue-1050.md` documenta a licao critica da rodada
`fv62kx` (batch24): um near-duplicate ja rejeitado no lote 17 foi
reintroduzido porque a verificacao de dedup do lote so comparou
candidatos entre si, nao contra o corpus inteiro -- e junto com isso
registra que `scripts/segmenter_semantic_audit.py`/`assign_splits` (via
`build_groups`) SAO a camada que deveria pegar isso automaticamente
comparando contra o corpus inteiro. Esta rodada descobriu, ao tentar
rodar exatamente essa camada antes de selecionar o proximo lote, que
ela estava de fato fazendo a comparacao contra o corpus inteiro (correto
por design) mas de forma ingenua O(n^2) com `SequenceMatcher.ratio()`
completo por par -- 191 documentos = 18.145 pares, ~27ms/par medido ao
vivo, ~493s so para essa etapa. Nenhum relatorio anterior notou isso
porque o corpus era menor nas rodadas passadas; o crescimento continuo
de #1050 (exatamente o objetivo da issue) e o que tornou o proprio
processo de verificacao do #1050 impraticavel. Esta rodada trata a
correcao desse gargalo como o proximo avanco natural e mais valioso
disponivel, servindo diretamente a continuidade de #1050 sem duplicar
o lote de ingestao ja em andamento em PR #1597.
