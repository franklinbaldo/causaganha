---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Fifteen real batches now proven through scripts/ingest_djen_sample_technique1_batch.py, run under alternating report mechanisms (legacy AgentRun scaffold and the current Wisk runtime) without needing a production-code change for most of them: batch1 (0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs (4 TJMS + 2 TJPA + 1 TJPI), first round to widen the candidate-length floor to 2500 chars and surface TJMS as a 25th tribunal; batch6 (Wisk round, PR #1549) 3 docs across TRF3/TJCE/TJMT (already-represented tribunals), targeting the 'preliminar' cue; batch7 (round zrek2s, PR #1553) 6 docs across TJRJ/TJGO/TJTO/TJPB/TJMA/TJRR, also targeting 'preliminar', and fixed a real production bug (see risk class 5 below); batch8 (round 83kr8s, PR #1552) 8 docs across TRF5/TJMT/TJRR/TJPA/TRF3/TJRJ/TJPB/TJES; batch9 (round hv2ep2, PR #1557) 6 docs across TJBA/TJMG/TJRS/TJSE/TRF2/TJCE (all already-represented tribunals, chosen for lowest store document-count rather than rare-category cue; hit a real concurrency collision of its own, see risk class 8 below); batch10 (round imy2ed, PR #1559) 2 docs targeting 'preliminar' (TJBA/574460089, TJRN/72797727) -- an initial selection (TJRN/72798564, TJBA/574460090) was reverted mid-round after discovering both were already-ingested duplicates (see risk class 9 below); batch11 (Wisk round, PR #1562) 2 docs, TJRN/72796443 and TJMA/42728353, both already-represented tribunals at the lowest store_count tier (2 each) -- no unused 'preliminar'-cue candidate remained anywhere in an already-represented tribunal after a fresh full scan, so this batch followed batch9's volume strategy instead; hit a new process defect, see risk class 10 below; batch12 (round 5lvbii, PR #1563) 2 docs, TJES/577054686 and TJGO/543562390, tied for the lowest non-singleton store_count (2 each) with a 'preliminar' cue each -- TJGO needed html.unescape() (364 raw HTML entities, no embedded markup) and a reviewed override for two pairs with no closing cue in the source (capitulo_merito, custas), verified against the raw text before declaring; batch13 (round 96cgqx, PR #1565) 2 docs, TJSE/578949084 (Acordao) and TJRS/458637070 (Sentenca), both the ONLY remaining eligible candidate for their respective tribunal (store_count=2 each, tied with TJPI/TJMG/TRF5/TRF2/TJTO) -- TJSE had 3 raw ASCII control characters (U+001C/U+001D as improvised quotes, U+0013 as an opening parenthesis), resolved with a length-preserving ASCII substitution (risk class 7); TJRS had embedded raw HTML markup, resolved with the batch3 cleaner (risk class 3); batch14 (this Wisk round) 3 docs, TST/237077355, TJPI/22443810, TRF5/349055692 -- a genuinely independent, concurrent session (this same round) picked the identical starting snapshot (121 documents) and the same volume-tier strategy as batch13, landing on TJSE/578949084 and TJRS/458637070 as well before either PR merged; discovered only as a merge conflict against origin/main after batch13 had already merged as PR #1565 (see risk class 12 below). Reconciled by keeping PR #1565's TJSE/TJRS as canonical and dropping this round's own re-ingestion of both (TJRS was a byte-identical duplicate document_id, no data loss; TJSE differed only in one substituted control character, so both sessions' TJSE ingestion could not both be kept without producing a true near-duplicate in the corpus). A sixth candidate this round selected before the merge, TJSC/587254906, was also reverted for an unrelated reason: it already existed in the store from batch4 (PR #1545), because data/segmenter_samples/tjsc_acordao.jsonl's own info.tribunal field is blank for every record in that file, silently breaking the (tribunal, id) dedup check against the store's real tribunal value (see risk class 11 below). batch15 (round j2t668, this round) 6 docs, TST/237077375, TJRJ/327515150, TJRJ/327497197, TJTO/285693071, TJTO/285710292, TRF2/301247724 -- all already-represented tribunals at the lowest store_count tier (2 each), continuing the volume-over-diversity strategy. A live pool scan this round found 218 eligible never-used real candidates still remaining across 17 tribunals, correcting a stale 'pool nearly exhausted' framing carried by prior next_move notes (that referred only to new-tribunal diversity, not remaining volume). Two candidates (TJTO/285693071, TRF2/301247724) hit the NBSP-to-space substitution defect pervasively (12 and 33 occurrences respectively, not a single isolated instance as in batch4/13) -- fixed by a new technique, not a manual patch: programmatically diffing the reconstructed (tags-stripped) text against source character-by-character, verifying every diff is exclusively NBSP-related, then reinserting the correct bytes into the tagged XML at the mapped positions and re-verifying byte-identical reconstruction before ingesting (see risk class 13 below). Four overrides were needed for dangling pairs with no closing cue (capitulo_merito x2, custas x2, honorarios x2, encerramento x1), all verified against the raw source text. document_count moved 61->68->74->81->86->93->96->102->109->115->117->119->121->123 (batch13)->126 (batch14)->132 (batch15), val/test ceiling 17/17 (batch9, 115 docs) ->18/18 (117-121 docs) ->19/19 (126 docs, batch14) ->20/20 (132 docs, batch15) -- recheck scripts/segmenter_governance_status.py live rather than trusting any cached number in this file, including this one. Still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked, fifteen rounds of proof the ingestion path scales without code changes (one real production bug found and fixed along the way by batch7 -- see risk class 5). A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py against the remaining pool in data/segmenter_samples/*.jsonl. Always verify document_count/tribunal distribution LIVE via scripts/segmenter_governance_status.py and SegmenterDatasetStore.list_documents() before selecting a batch's candidates -- this backlog file's own numbers have repeatedly lagged real state between concurrent rounds (multiple independent sessions picked up the same next_move within the same day for batches 6-14, batches 13 and 14 even picking the exact same two candidates independently -- see risk class 12); do not trust last_verified_run_id's snapshot without a live re-check, and expect another concurrent session to be working this same issue at any given moment. Before spawning an annotation subagent for a candidate, dedupe it correctly per risk class 9 below (content_hash(text) + (tribunal, id_documento)-vs-source_uri, NOT any externally-sourced hash field) -- AND per risk class 11, derive the tribunal side of that pair from the jsonl FILENAME, not from the candidate record's own info.tribunal field, since at least one file (tjsc_acordao.jsonl) has that field blank for every record. After a dry-run ingest, always verify each returned document_id against the real store's documents/<id>.xml before writing for real (git status --short data/segmenter after a REAL ingest is the reliable tell: a candidate that produces only a new annotations/<id>/ann_*.xml with no matching new documents/<id>.xml was already in the store -- revert that annotation file, it adds no independence value if its annotator_config matches the pre-existing one), AND keep the tagged-annotation directory passed to --tagged-dir free of any file that shares a bare `<id_documento>.txt` name with a source/candidate file -- see risk class 10 below, a real batch11 near-miss. Before opening a PR, fetch and diff against the current origin/main tip (not just the branch's own stale base) to catch a same-candidate collision with a concurrent session's already-merged batch before it becomes a merge conflict -- see risk class 12. Tribunal-diversity mining is exhausted only for a couple of specific tribunals (TRF6/TJSC, store_count=1 each, no eligible candidate left below the 2500-char floor) -- a live full-pool scan after batch15 (field names `text`/`info.id`, NOT `texto_limpo`/`id_documento` -- an earlier scan using the wrong field names undercounted to zero and wrongly suggested the whole pool was nearly exhausted, see risk class 13) found 218 eligible, never-used real candidates still remaining across 17 tribunals, so volume growth is far from supply-constrained. The path forward remains picking unused Sentenca/Acordao candidates from already-represented tribunals by volume (lowest store_count first), not chasing new tribunals or a specific rare category; after batch15, TJMG/TJGO/TJES (2-3 each) are the next-lowest tier once TST/TJRJ/TJTO/TRF2 (this batch's picks) move up. When a start/end pair has no closing cue in the source text (a recurring, expected shape, not a bug -- see risk classes 4/6), verify against the raw source text before declaring a --allowed-unmatched-overrides reason, same as every prior batch that hit this. A source jsonl with raw HTML markup (<b>/<table>/<br>/etc, not just entities) needs the batch3 HTML-to-text cleaner (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py) BEFORE handing the text to an annotation subagent, not just html.unescape() -- batch13/14 found this the hard way for TJSC, TJRS and TST, each requiring a redo after the first annotation attempt silently reproduced the markup or hit malformed-XML. IMPORTANT for whichever mechanism picks this up next: knowledge/agent-runs/index.md and .claude/hourly-loop.md declare the legacy AgentRun mechanism (this file's own historical updates through batch10 came from that mechanism) deprecated in favor of the Wisk runtime (.wisk/knowledge/) for the CausaGanha hourly loop -- batches 6, 7, 11 and 14 ran under Wisk, batch12/13 ran under the legacy AgentRun scaffold again (its scheduled prompt still hard-codes it; the conflict was escalated once via notification on 2026-09-14/to0ars and reconfirmed unchanged by every AgentRun round since). This BacklogItem type is not itself named in the deprecation list (only AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck are), so it is kept updated here regardless of which mechanism a future round uses, but check .wisk/knowledge/ too before assuming this file alone is current. Budget for thirteen known defect/risk classes before trusting a batch's first pass -- see the numbered list below, including risk class 5 (a real production fix, already merged) and risk classes 7-13 (candidate-selection/concurrency/tooling process bugs, not production-code bugs)."
last_verified_run_id: "2026-09-16-exciting-mccarthy-j2t668"
last_verified_at: "2026-09-16T21:50:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Oito rodadas reais já provaram o mecanismo de
ingestão (`scripts/ingest_djen_sample_technique1_batch.py`), rodando sob
dois mecanismos de relatório que se alternam (AgentRun legado e Wisk) sem
exigir mudança de código de produção na maioria delas:

- **Lote 1** (rodada 0iuk22): 7 documentos, 7 tribunais (TJMT, TJPA, TRF3,
  TJCE, TJES, TRF5, TJSE). `document_count` 61->68, teto de val/test 9->10.
- **Lote 2** (rodada jyqinl): 6 documentos, 6 tribunais novos (TJPB,
  TJRN, TJRJ, TJMA, TJBA, TJRR). `document_count` 68->74, teto de val/test
  10->11
  (`docs/planning/evidence/segmenter-djen-sample-batch2-2026-09-16.json`).
- **Lote 3** (rodada uyx7xc): 7 documentos, 7 tribunais novos (TJGO,
  TJPI, TJMG, TJRS, TJTO, TRF2, TST). `document_count` 74->81, teto de
  val/test 11->12
  (`docs/planning/evidence/segmenter-djen-sample-batch3-2026-09-16.json`).
- **Lote 4** (rodada mg2tp1): 5 documentos, 3 tribunais novos (TJSC,
  TRF4 x3, TRF6). `document_count` 81->86, teto de val/test 12->13
  (`docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json`).
- **Lote 5** (rodada la7bsl): 7 documentos (4 TJMS + 2 TJPA + 1 TJPI).
  Primeira rodada a alargar o piso de tamanho de candidato para 2500
  caracteres, o que revelou TJMS como 25º tribunal. `document_count`
  86->93, teto de val/test 13->14. Achado: normalização CRLF->LF
  necessária antes de gerar candidates.json (fidelidade verbatim do XML).
- **Lote 6** (rodada Wisk, commit `1f1ef1d`, PR #1549): 3 documentos
  (TRF3, TJCE, TJMT -- tribunais já representados), visando a
  categoria mais rara (`preliminar`). `document_count` 93->96. Primeira
  rodada desta linhagem a rodar sob o mecanismo Wisk em vez do scaffold
  AgentRun -- confirma que os dois mecanismos agora se alternam na mesma
  linhagem de issue.
- **Lote 7** (rodada zrek2s, PR #1553): 6 documentos (TJRJ, TJGO, TJTO, TJPB, TJMA,
  TJRR), também visando `preliminar`. `document_count` 96->102, teto de
  val/test 14->15
  (`docs/planning/evidence/segmenter-djen-sample-batch7-2026-09-16.json`).
  Encontrou e corrigiu no código de produção um defeito novo (ver classe
  5 abaixo) e estendeu a allowlist de falsos positivos do audit semântico
  com uma verificação real contra o texto-fonte.
- **Lote 8** (esta rodada, 83kr8s -- desenvolvida em paralelo aos lotes 6
  e 7 sob o mesmo rótulo "sexto lote" antes de qualquer uma mesclar,
  sem coordenação prévia): 8 documentos, todos em tribunais já
  representados (TRF5, TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES).
  `document_count` 93->101 em isolamento (arquivo de evidência ainda
  rotulado `batch6` -- ver nota acima sobre a colisão de nomes),
  109 ao vivo após o merge com os lotes 6 e 7 concorrentes (confirmado
  por `scripts/segmenter_governance_status.py` -- um a menos que a soma
  ingênua 96+6+8=110, provavelmente uma deduplicação por hash de
  conteúdo entre candidatos de rodadas concorrentes, inofensiva).
- **Lote 9** (rodada hv2ep2, PR #1557): 6 documentos (TJBA, TJMG, TJRS,
  TJSE, TRF2, TJCE), todos em tribunais já representados, escolhidos pelo
  menor `store_count` (1 documento cada, antes deste lote) em vez de
  mirar a categoria rara `preliminar` -- objetivo foi crescimento de
  volume, não diversidade de categoria. `document_count` 109->115, teto
  de val/test 16->17
  (`docs/planning/evidence/segmenter-djen-sample-batch8-2026-09-16.json`
  -- rotulado "batch8" no nome do arquivo por ser o próximo rótulo
  numérico livre entre os arquivos de evidência já commitados; esta
  prosa numera "lote 9" na sequência histórica real -- mesma deriva de
  numeração do lote 6/8, inofensiva, cruzar por `round_id`, não por
  número). Concorrência real de novo: o primeiro candidato escolhido
  (TRF6/593231752) já havia sido ingerido por uma sessão concorrente
  entre o escaneamento inicial do store desta rodada e a tentativa de
  ingestão -- trocado por TJCE/363647741 (ver classe de risco 8 abaixo).
  Mecanismo de anotação novo: inserção de tags baseada em offset
  (`str.find` no texto original, inserções aplicadas de trás para
  frente) em vez de reescrever a reprodução manualmente -- torna um
  mismatch de fidelidade verbatim estruturalmente impossível para
  qualquer âncora aceita pelo helper, e converteu os dois achados de
  NBSP/caractere de controle abaixo em `ValueError` imediato e ruidoso
  em vez de corrupção silenciosa só pega depois pelo validador mecânico.
- **Lote 10** (rodada imy2ed, esta mescla): 2 documentos visando
  `preliminar` (TJBA/574460089, TJRN/72797727), ambos em tribunais já
  representados com apenas 1 documento cada. `document_count` 109->111
  em isolamento (antes do lote 9 mesclar), 117 ao vivo apos mesclar com
  o lote 9 (115+2). Uma primeira seleção (TJRN/72798564, TJBA/574460090)
  foi ingerida e **revertida** ainda nesta rodada -- ver classe de risco
  9 abaixo (renumerada apos a mescla, era "7" no rascunho desta rodada
  antes de colidir com as classes 7/8 ja mescladas do lote 9): os dois
  candidatos já tinham sido ingeridos por um lote anterior sob o mesmo
  `(tribunal, id_documento)`, e a checagem de deduplicação inicial
  comparou o hash errado, deixando passar. Nenhum commit/push referenciou
  os candidatos errados; a correção aconteceu inteiramente antes do
  primeiro `git add`.
- **Lote 11** (rodada Wisk, esta mescla): 2 documentos, TJRN/72796443 e
  TJMA/42728353, ambos em tribunais já representados no nível mais baixo
  de `store_count` (2 cada). Um scan completo e correto (usando `info.id`/
  `info.tribunal`/`info.tipoDocumento`/`text`, os nomes reais dos campos
  em `data/segmenter_samples/*.jsonl` -- não `id_documento`/`texto_limpo`,
  que só existem no formato de `candidates.json` já processado) contra
  todos os 849 registros disponíveis não encontrou nenhum candidato
  `preliminar` não usado em tribunal já representado -- confirma que a
  categoria rara está esgotada nesse universo, não só nos tribunais
  batch6/7/10 já tentaram. Um par TST/Acórdão (`237077355`/`237077375`)
  foi cogitado e descartado: ambos reproduzem o mesmo acórdão
  (`TST-AIRR-0094800-39.1997.5.20.0003`) diferindo só no nome da parte
  no rodapé "Intimado(s)/Citado(s)" -- ingerir os dois infralaria
  `document_count` sem diversidade real de treino, o mesmo anti-padrão
  que o piso de escala do corpus (RFC 0012 §5 item 4) existe para evitar.
  `document_count` 117->119 (confirmado ao vivo), teto de val/test
  inalterado em 18/18 (2 documentos não foi suficiente para cruzar o
  próximo degrau do teto). Ambos os candidatos tinham texto limpo (sem
  CRLF/NBSP/caracteres de controle/HTML bruto) -- nenhuma das classes
  2-7 precisou de mitigação nesta rodada. Encontrou um defeito de
  processo novo (não de código de produção), ver classe de risco 10
  abaixo: um "quase-erro" pego e revertido antes do primeiro `git add`.
- **Lote 12** (rodada AgentRun 5lvbii, esta mescla): 2 documentos,
  TJES/577054686 e TJGO/543562390, empatados no menor `store_count`
  não-singleton (2 cada), ambos com cue `preliminar`. Reconfirmou ao
  vivo que os tribunais citados como "esgotados" (STM, TJAC, TJAM,
  TJAP, TJPE, TJSP, TRF1, e agora também TJSC/TRF6) continuam sem
  candidato elegível após excluir os arquivos auxiliares
  `*_annotation_gold`/`*_annotation_raw` do scan (esses não têm o campo
  `info` com `id`/`tribunal`/`tipoDocumento`, são material de outro
  experimento, não candidatos de ingestão). TJGO tinha 364 entidades
  HTML brutas no `text` (`&nbsp;`, `&Aacute;`, etc., sem markup
  embutido) -- resolvido com `html.unescape()` (mesma correção das
  classes 2/6). Primeira tentativa de ingestão: TJES passou direto;
  TJGO falhou por dois pares pendentes sem cue de fechamento
  (`capitulo_merito`, `custas`) -- verificado contra o texto-fonte bruto
  antes de declarar um override revisado (mesmo padrão das classes 4/6):
  "Decido." abre o mérito sem nenhuma frase de transição antes da
  próxima seção, e custas/honorários são fixados na mesma frase, com só
  honorários recebendo um encerramento textual distinto. Após o
  override, ambos ingeridos. `document_count` 119->121 (confirmado ao
  vivo), teto de val/test inalterado em 18/18. Audit semântico não
  encontrou nenhum achado novo nos dois documentos. Nenhuma classe de
  risco nova -- todos os defeitos encontrados já eram conhecidos.
- **Lote 13** (rodada AgentRun 96cgqx, esta mescla): 2 documentos,
  TJSE/578949084 (Acórdão) e TJRS/458637070 (Sentença) -- cada um o
  **único** candidato elegível restante para seu tribunal (ambos em
  `store_count=2`, empatados com TJPI/TJMG/TRF5/TRF2/TJTO), ingeridos
  antes que uma sessão concorrente os consumisse. Achado que corrige o
  lote 11: a categoria rara `preliminar` **não** está esgotada no
  universo inteiro -- um scan ao vivo restrito só aos 8 tribunais no
  menor `store_count` encontrou dezenas de candidatos `preliminar` não
  usados (TRF2 22, TJTO 28, TRF5 20, TJRJ 10, TJPI 5); a conclusão do
  lote 11 estava correta apenas para os tribunais que ele checou naquele
  momento, não é uma propriedade permanente do pool -- sempre re-scanear
  ao vivo o conjunto especifico de tribunais em vez de confiar na
  conclusão de esgotamento de um lote anterior. TJSE tinha 3 caracteres
  de controle ASCII (`\x1c`/`\x1d` como aspas improvisadas em torno de
  uma citação do STF, `\x13` como parêntese de abertura antes de uma
  referência de página) -- resolvido com substituição preservando o
  comprimento (classe de risco 7, mesmo padrão do lote 9). TJRS tinha
  markup HTML bruto embutido (`<b>`/`<table>`/`<tr>`/`<td>`) -- limpo
  com o cleaner do lote 3. Ambos caíram no mesmo par pendente
  `custas`+`honorarios` compartilhando a frase final de fechamento sem
  cue distinto (classe de risco 1) -- verificado contra o texto-fonte
  bruto de cada um antes de declarar o override. `document_count`
  121->123 (confirmado ao vivo), teto de val/test inalterado em 18/18.
  Audit semântico não encontrou nenhum achado novo nos dois documentos
  (9 achados totais, todos pré-existentes e já na allowlist). Nenhuma
  classe de risco nova.
- **Lote 14** (esta rodada, Wisk): 3 documentos, TST/237077355,
  TJPI/22443810, TRF5/349055692 -- a parte não sobreposta do que esta
  sessão originalmente selecionou como 6 candidatos, depois que um
  merge contra `origin/main` revelou colisão com o lote 13 (mesclado
  concorrentemente como PR #1565 a partir do mesmo snapshot de 121
  documentos) para TJRS e TJSE, e com o lote 4 para TJSC (ver classes de
  risco 11 e 12, a última nova nesta rodada). `document_count`
  123->126 (após o lote 13), teto de val/test 18/18->19/19. TST tinha
  markup HTML bruto na fonte (tags `<br>`) -- limpo com o cleaner do
  lote 3. Nenhum achado novo do audit semântico nos 3 documentos.

**Por que continua aberta:** o piso de RFC 0012 §5 item 4 (>=30 val,
>=30 teste, cada um adjudicado) continua exigindo algo perto de 200
documentos totais; estamos em 126 apos mesclar os lotes 13 e 14 (recheque
ao vivo antes de confiar neste número, dado o ritmo de rodadas
concorrentes neste mesmo dia -- duas sessões já colidiram no mesmo
candidato uma vez, ver classe de risco 12). A mineração por diversidade
de tribunal está praticamente esgotada (restam apenas STM, TJAC, TJAM,
TJAP, TJPE, TJSP, TRF1 sem candidato usável, reconfirmado pelo lote 12)
-- os lotes 6-14 confirmam que o caminho daqui em diante é escolher mais
candidatos não usados em tribunais já representados por volume (menor
`store_count` primeiro): TJMG/TJRJ/TJTO/TRF2/TJGO/TJES estão no menor
nível não esgotado apos o lote 14 (TJSC/TRF6/TST, o nível usado pelos
lotes 13/14, estão esgotados ou abaixo do piso de tamanho). A categoria
rara `preliminar` **não** está esgotada nesse universo -- o lote 13
encontrou dezenas de candidatos não usados nos próprios tribunais do
menor nível (ver acima); o "esgotamento" relatado pelo lote 11 era
escopo apenas dos tribunais checados naquele momento.

**Nove classes de risco/defeito já mapeadas para o próximo lote:**

1. Pares pendentes sem cue de fechamento (`capitulo_merito`/`custas`/
   `honorarios`/`relatorio`/`ementa`) — toda rodada até agora precisou de
   override manual revisado para pelo menos um documento
   (`docs/planning/evidence/segmenter-djen-sample-batch7-overrides.json`
   para os 4 documentos/7 categorias do lote 7,
   `docs/planning/evidence/segmenter-djen-sample-batch6-overrides.json`
   para os 6 documentos/13 categorias do lote 8 -- ambos os formatos
   recorrentes: `custas`+`honorarios` dividindo uma única frase do
   dispositivo sem cue de fechamento separado para nenhum dos dois, um
   export "capa+ementa-estruturada" sem RELATORIO/VOTO para fechar
   `ementa`/`relatorio`, ou um "relatório dispensado" de Juizado Especial
   sem cue de fechamento).
2. Alguns candidatos têm o campo `texto_limpo` com entidades HTML
   literais não decodificadas — resolvido por `html.unescape()`.
3. Alguns candidatos têm `texto_limpo` com markup HTML bruto (às vezes
   malformado) embutido — checar `ET.fromstring(f"<text>{texto}</text>")`
   antes de atribuir a um subagente e reusar
   `docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`.
4. Uma substituição de mesmo comprimento (ex.: NBSP->espaço comum) que o
   check de comprimento da fidelidade verbatim sozinho não pega — diffar
   programaticamente.
5. **CORRIGIDO NO CÓDIGO DE PRODUÇÃO no lote 7**:
   `scripts/ingest_djen_sample_technique1_batch.py`'s `_parse_tagged`
   chamava `tagged_text.strip()` antes de envolver em XML, e o
   `str.strip()` do Python trata U+00A0 (espaço não separável) como
   whitespace — um documento-fonte cujo `texto_limpo` genuinamente abre
   ou fecha com NBSP tinha esse conteúdo descartado silenciosamente,
   produzindo um falso mismatch de fidelidade verbatim. Corrigido para
   `tagged_text.strip("\n\r\t ")` (só ASCII), com teste de regressão
   (`test_ingest_preserves_leading_nbsp_and_blank_lines`) — lotes futuros
   não precisam mais contornar isso manualmente. Também ficar atento a
   `scripts/segmenter_semantic_audit.py`'s heurística `*_collapsed`
   sinalizando falso positivo quando a mesma cifra/citação se repete na
   narrativa antes da tag operativa (formato já documentado e esperado —
   ver a allowlist de `tests/segmenter_dataset/test_segmenter_audit_scripts.py`;
   verificar cada achado novo contra o texto-fonte antes de estender a
   allowlist, nunca silenciar o assert).
6. Candidatos com `texto_limpo` contendo quebras de linha CRLF (`\r\n`)
   quebram o check de fidelidade verbatim de forma estrutural — a
   normalização obrigatória de fim de linha da especificação XML (seção
   2.11) torna `\r\n` irrecuperável pelo mecanismo de reconstrução
   existente independentemente da qualidade da anotação (achado do lote
   5). Normalizar `texto_limpo` para LF antes de virar candidato.
7. **NOVO (lote 9)**: alguns candidatos têm caracteres de controle ASCII
   literais (ex.: U+001C/U+001D, file/group separator) embutidos como
   aspas improvisadas no meio da frase (`RUBRICA \x1cPAGTO COBRANÇA
   ASPECIR\x1d`). XML 1.0 proíbe esses code points mesmo depois do fix
   de `strip()` do lote 7 (que só cobre whitespace) — `ET.fromstring`
   falha com "not well-formed (invalid token)" apontando o byte
   literal, sem relação com a anotação em si. Substituir por aspas ASCII
   comuns (substituição que preserva o comprimento, mesmo espírito do
   fix de NBSP da classe 4) antes de anotar.
8. **NOVO (lote 9)**: o dedup por hash de conteúdo feito durante a
   *seleção* de candidatos (antes da limpeza de HTML) pode não bater com
   o hash gravado no store para o mesmo documento se aquele candidato
   precisar de limpeza de HTML (classe 3) — o hash do store é sobre o
   texto já limpo, não sobre o HTML bruto do arquivo jsonl de origem, de
   modo que o dedup de seleção some negativo mesmo quando o documento já
   existe. Isso só importa para achar duplicatas de *rodadas
   concorrentes*, já que dentro da própria rodada o candidato é
   comparado consigo mesmo; mitigação usada no lote 9: depois do dry-run
   de ingestão, checar cada `document_id` retornado contra
   `data/segmenter/documents/<id>.xml` no store real antes de gravar de
   fato — se já existir, é uma colisão de concorrência (não um bug desta
   rodada), descartar o candidato e escolher outro em vez de investigar
   mais.
9. **NOVO (lote 10)**: deduplicar candidatos comparando o hash ERRADO
   não detecta nada -- classe distinta da 8 (que e sobre o momento da
   selecao vs. estado do store; esta e sobre comparar o espaco de hash
   errado desde o inicio). O `sha256` que vem em
   `data/segmenter_samples/*.jsonl`'s `info` é o hash da DJEN sobre o
   artefato bruto original — um espaço de hash completamente diferente
   de `SegmenterDatasetStore`'s próprio `source.source_hash`, que é
   `segmenter_dataset.dedup.content_hash(text)` (SHA-256 sobre o texto
   normalizado). Comparar um contra o outro nunca detecta um duplicado
   real. `segmenter_dataset.ids.document_id()` deriva o ID a partir de
   `(source_system, source_uri, source_hash=content_hash(text))` — a
   única checagem correta antes de gastar uma chamada de subagente é
   recalcular `content_hash(text)` com a mesma função que o store usa,
   **e** verificar `(tribunal, id_documento)` diretamente contra os
   `source_uri` já existentes (formato
   `djen_sample_technique1:batch1:{tribunal}:{id}` — o literal
   `"batch1"` é uma constante fixa em todo lote, não o número real do
   lote). Como `store.write_document()` é deliberadamente idempotente
   (RFC 0012 §3.1, `ImmutabilityError` só dispara se o conteúdo diferir),
   um candidato já ingerido some silenciosamente da mensagem "Ingested N
   document(s)" — ela reporta sucesso de escrita da *anotação*, não se o
   documento era novo. A unica forma confiavel de pegar isso é checar
   `git status --short data/segmenter` depois de ingerir (mesma
   mitigação da classe 8, generalizada): se nenhum arquivo novo aparecer
   em `documents/`, o "novo" documento já existia e a anotação
   recém-criada é redundante (mesmo `annotator_id` fixo de sempre, sem
   valor de segunda anotação independente para #1051) e deve ser
   revertida, não mantida.
10. **NOVO (lote 11)**: `--tagged-dir` não pode compartilhar diretório com
    os arquivos-fonte brutos. `ingest_djen_sample_technique1_batch.py`
    varre `tagged_dir.glob("*.txt")` e usa `Path.stem` (o nome do arquivo
    sem a última extensão) como chave contra `candidates.json`'s
    `id_documento`. Se o texto-fonte bruto de um candidato também mora em
    `<id_documento>.txt` no mesmo diretório (nomeação natural ao salvar
    texto para um subagente ler) e a saída tagueada do subagente for
    salva como `<id_documento>.tagged.txt`, o glob casa **o arquivo
    errado**: `stem("72796443.txt")` == `"72796443"` (bate com a chave),
    enquanto `stem("72796443.tagged.txt")` == `"72796443.tagged"` (não
    bate com nada) -- o script silenciosamente ingere o texto-fonte
    *sem nenhuma tag* como se fosse a anotação real (reconstrução
    verbatim passa trivialmente, porque o "texto tagueado" é o próprio
    texto-fonte sem tags), produzindo um documento com `covered_categories`
    completo mas zero `TextLabel`s -- um defeito silencioso, sem erro,
    sem entrada em `Skipped`. Pego nesta rodada só porque
    `git status --short data/segmenter` (mitigação já recomendada pela
    classe 9) mostrou um novo `documents/<id>.xml` cujo conteúdo de
    anotação (`ann_*.xml`) tinha `covered_categories` mas nenhum `<label>`
    -- revertido (arquivo não rastreado, `rm` direto) antes do primeiro
    `git add`. Mitigação: sempre usar um diretório de saída **separado**
    para os arquivos tagueados (ex.: `.../tagged/<id_documento>.txt`,
    nunca `.../<id_documento>.tagged.txt` no mesmo diretório dos
    textos-fonte), e inspecionar cada anotação recém-escrita
    (`cat data/segmenter/annotations/<id>/ann_*.xml | grep -c '<label'`)
    antes de confiar na mensagem "Ingested N document(s)" -- ela não
    distingue uma anotação real de uma vazia.
11. **NOVO (lote 13)**: o campo `info.tribunal` de um `data/segmenter_samples/*.jsonl`
    pode estar em branco para TODOS os registros de um arquivo (confirmado
    para `tjsc_acordao.jsonl`), mesmo quando o nome do arquivo deixa o
    tribunal óbvio. Se o dedup de seleção (classe 9) usar esse campo em vez
    do nome do arquivo, a chave `(tribunal, id_documento)` fica `('',
    id_documento)` e nunca bate contra a chave real do store
    (`('TJSC', id_documento)`), deixando passar um candidato já ingerido.
    Pego só depois da anotação e ingestão real: `git status --short
    data/segmenter` mostrou uma nova `annotations/<id>/ann_*.xml` sem a
    correspondente `documents/<id>.xml` nova (mitigação da classe 9,
    generalizada de novo) -- o documento (TJSC/587254906) já existia desde
    o lote 4 (PR #1545). A anotação nova foi revertida (`rm` direto,
    arquivo não rastreado) em vez de mantida, porque seu
    `annotator_config` (mesmo `model_family`, `seeded_with: none`) era
    idêntico ao da anotação pré-existente -- não conta como segunda
    anotação independente para #1051/IAA (`annotations_are_independent`),
    então era puro custo de duplicata sem nenhum valor de adjudicação.
    Mitigação: ao montar a chave de dedup, derivar o tribunal do NOME DO
    ARQUIVO jsonl (já conhecido pela convenção `<tribunal_lower>[_tipo].jsonl`),
    não do campo `info.tribunal` do registro -- e depois de qualquer
    ingestão real, sempre conferir `git status --short data/segmenter`
    inteiro (não só a lista de IDs retornada pelo script) antes do primeiro
    `git add`.
12. **NOVO (lote 14)**: duas sessões independentes podem escanear o mesmo
    pool ao vivo, empatar no mesmo tribunal de menor `store_count`, e
    escolher o **mesmo** candidato -- sem que o dedup de nenhuma das duas
    detecte nada, porque cada sessão trabalha em sua própria branch local
    e o candidato só existe no store da OUTRA sessão depois que ela faz
    merge. Diferente das classes 8-10 (uma sessão descobre que seu próprio
    scan ficou desatualizado por uma escrita concorrente), aqui é a
    *seleção* de duas sessões que colide, e só aparece como um merge
    conflict (ou pior, um merge silencioso) depois que a primeira PR já
    mesclou. Neste caso (lote 13 vs lote 14, mesmo snapshot de 121
    documentos): TJRS/458637070 -- ambas sessões rodaram o mesmo limpador
    HTML->texto sobre o mesmo texto-fonte bruto e produziram texto limpo
    byte-a-byte idêntico, então o `document_id` (hash do texto limpo)
    bateu exatamente e o merge foi um no-op silencioso para o documento
    (mas a segunda anotação, com `annotator_config` idêntico à primeira,
    não teve valor de independência e foi revertida). TJSE/578949084 --
    as duas sessões escolheram substituições ASCII *diferentes* para o
    mesmo caractere de controle bruto (uma usou `-`, a outra usou `(`),
    produzindo `document_id`s genuinamente diferentes para o mesmo
    documento real -- manter os dois teria sido um near-duplicate real no
    corpus (mesmo anti-padrão que o lote 11 rejeitou para um par TST quase
    idêntico), então a versão da sessão cujo PR mesclou primeiro foi
    mantida como canônica e a da outra sessão foi revertida antes do
    commit final. Mitigação: antes de abrir a PR (não só antes de
    selecionar candidatos), buscar e comparar contra o `origin/main` atual
    -- um `mergeable_state` sujo é o sinal mais cedo de uma colisão de
    seleção como esta; ao resolver, escolher UMA versão canônica por
    documento (normalmente a que já mesclou) e reverter a anotação
    redundante da outra sessão se o `annotator_config` for idêntico.

## Lote 14 (esta rodada, Wisk)

3 documentos reais, novos e não sobrepostos com o lote 13 (PR #1565, que
mesclou concorrentemente): TST/237077355, TJPI/22443810, TRF5/349055692.
`document_count` 121->126 (via 123 do lote 13 já mesclado + 3 deste lote),
teto de val/test 18/18->19/19. Esta sessão originalmente selecionou 6
candidatos (os 3 acima, mais TJSC/587254906, TJRS/458637070 e
TJSE/578949084) antes de descobrir, ao tentar abrir a PR, que main já
tinha avançado: TJSC já existia desde o lote 4 (ver classe de risco 11);
TJRS e TJSE colidiram com o lote 13, mesclado concorrentemente enquanto
esta sessão trabalhava (ver classe de risco 12, nova). TJRS foi um no-op
(texto limpo idêntico, mesmo `document_id`); TJSE precisou reverter esta
sessão's própria ingestão e manter a do lote 13 (documents_id diferentes
por uma substituição de caractere de controle distinta). TST tinha markup
HTML bruto na fonte (apenas tags `<br>`) e precisou do limpador
`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py` antes
da anotação. Três overrides `--allowed-unmatched-overrides` foram
necessários (ementa em TJPI; capitulo_merito+voto em TST;
relatorio+custas+honorarios em TRF5), todos verificados contra o
texto-fonte bruto antes de declarar. `uv run pytest -q
tests/segmenter_dataset/` verde (391 testes, incluindo os novos testes de
regressão `test_real_store_reflects_batch13_corpus_growth` -- do lote 13,
já mesclado -- e `test_real_store_reflects_batch14_corpus_growth`, deste
lote); `uv run pytest -q` completo (repo inteiro) também verde; audit
semântico sem novos achados para os 3 documentos deste lote.

## Lote 15 (esta rodada, AgentRun j2t668)

6 documentos reais, novos e não sobrepostos com qualquer lote anterior:
TST/237077375, TJRJ/327515150, TJRJ/327497197, TJTO/285693071,
TJTO/285710292, TRF2/301247724 -- todos em tribunais já representados no
tier de menor `store_count` (2 cada), continuando a estratégia de
crescimento por volume (não diversidade de tribunal) do `next_move`
explícito da rodada anterior (zrek2s).

Um scan ao vivo do pool completo no início desta rodada, usando os nomes
de campo corretos do jsonl (`text`/`info.id`, não `texto_limpo`/
`id_documento` como um scan anterior mal escrito teria sugerido),
encontrou **218 candidatos reais elegíveis e nunca usados** ainda no
pool, distribuídos por 17 tribunais -- corrigindo a framing de "pool
quase esgotado" que rodadas anteriores vinham carregando (essa framing
se referia apenas à diversidade de tribunal novo, não ao volume restante
nos tribunais já representados). Ver risco classe 13 abaixo.

Quatro candidatos (TST, TJTO x2, TRF2) tinham markup HTML bruto embutido
em `texto_limpo` (`<br>` solto, `<b>`/`<table>`/`</br>`, wrapper completo
`<html><head>...<body>`) e precisaram do limpador já validado do lote 3
(`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`)
antes da anotação.

Dois candidatos (TJTO/285693071, TRF2/301247724) tiveram o defeito já
conhecido de substituição NBSP (U+00A0) → espaço comum durante a
transcrição do subagente, mas de forma pervasiva (12 e 33 ocorrências
respectivamente em todo o documento, não uma única instância isolada
como nos lotes 4/13) -- corrigido programaticamente, sem retipar nada
manualmente e sem pedir redo ao subagente: um diff de
`difflib.SequenceMatcher` entre o texto reconstruído (tags removidas) e
o texto-fonte, verificando que TODA diferença é exclusivamente
relacionada a NBSP antes de tocar em qualquer coisa, reinserindo os
bytes corretos na posição mapeada dentro do XML marcado, e reverificando
byte-a-byte antes de ingerir (ver risco classe 13 abaixo).

Quatro overrides `--allowed-unmatched-overrides` foram necessários para
pares pendentes sem cue de fechamento (`capitulo_merito` x2, `custas`
x2, `honorarios` x2, `encerramento` x1), todos verificados contra o
texto-fonte bruto antes de declarar -- mesma classe de defeito já
estabelecida em lotes anteriores (menção formulaica tipo "Sem custas nem
honorários advocatícios" embutida no dispositivo, sem frase de
fechamento distinta).

`scripts/segmenter_governance_status.py` confirma `document_count`
126->132, `annotation_count` 179->185, teto de val/test 19/19->20/20
(ver `git status --short data/segmenter` desta rodada: exatamente 6
novos `documents/*.xml` e 6 novos `annotations/<id>/`, sem write no-op
silencioso). `uv run ruff check`/`format --check` limpos. Audit
semântico (`scripts/segmenter_semantic_audit.py`) sem nenhum novo
achado para os 6 documentos deste lote -- todos os achados sinalizados
já estavam na allowlist de rodadas anteriores ou pertencem a documentos
pré-existentes (não deste lote).

**Classe de risco 13 (nova)**: um scan do pool de candidatos que usa os
nomes de campo ERRADOS do jsonl (`texto_limpo`/`id_documento`, os nomes
usados pelo formato de `candidates.json` já processado pelo script de
ingestão) em vez dos nomes REAIS do jsonl bruto em
`data/segmenter_samples/*.jsonl` (`text`/`info.id`) retorna
silenciosamente zero candidatos elegíveis, em vez de um erro -- e uma
rodada que confia nesse resultado (como uma nota `next_move` anterior
parece ter feito) conclui erroneamente que o pool está esgotado, quando
na realidade há centenas de candidatos ainda disponíveis. Mitigação:
antes de declarar um tribunal ou o pool inteiro "esgotado", inspecionar
uma amostra bruta de `data/segmenter_samples/*.jsonl` com
`json.loads()` e conferir as chaves reais (`text`, `info.tribunal`,
`info.tipoDocumento`, `info.id`) em vez de assumir os nomes de campo do
formato pós-processado.

Além disso, o mesmo defeito de NBSP pervasivo (não apenas uma ocorrência
isolada) exige a técnica de diff-e-remapeamento programático descrita
acima em vez do patch manual de substring usado em lotes anteriores
(batch4/13) -- um patch manual não escalaria para dezenas de ocorrências
por documento.
