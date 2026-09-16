---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Ten real batches now proven through scripts/ingest_djen_sample_technique1_batch.py, run under two alternating report mechanisms (legacy AgentRun scaffold and a new Wisk runtime) without needing a production-code change for most of them: batch1 (0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs (4 TJMS + 2 TJPA + 1 TJPI), first round to widen the candidate-length floor to 2500 chars and surface TJMS as a 25th tribunal; batch6 (Wisk round, PR #1549) 3 docs across TRF3/TJCE/TJMT (already-represented tribunals), targeting the 'preliminar' cue; batch7 (round zrek2s, PR #1553) 6 docs across TJRJ/TJGO/TJTO/TJPB/TJMA/TJRR, also targeting 'preliminar', and fixed a real production bug (see risk class 5 below); batch8 (round 83kr8s, PR #1552) 8 docs across TRF5/TJMT/TJRR/TJPA/TRF3/TJRJ/TJPB/TJES; batch9 (round hv2ep2, PR #1557) 6 docs across TJBA/TJMG/TJRS/TJSE/TRF2/TJCE (all already-represented tribunals, chosen for lowest store document-count rather than rare-category cue; hit a real concurrency collision of its own, see risk class 8 below); batch10 (round imy2ed, this merge) 2 docs targeting 'preliminar' (TJBA/574460089, TJRN/72797727) -- an initial selection (TJRN/72798564, TJBA/574460090) was reverted mid-round after discovering both were already-ingested duplicates (see risk class 9 below, renumbered from imy2ed's own draft '7' after merging with batch9's already-merged risk classes 7/8). document_count moved 61->68->74->81->86->93->96->102->109->115->117 (117 confirmed live after merging batch9 (115) and batch10's isolated +2), val/test ceiling 17/17 (batch9, 115 docs) ->18/18 (confirmed live after the merge, 117 docs) -- recheck scripts/segmenter_governance_status.py live rather than trusting any cached number in this file, including this one. Still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked, ten rounds of proof the ingestion path scales without code changes (one real production bug found and fixed along the way by batch7 -- see risk class 5). A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py against the remaining pool in data/segmenter_samples/*.jsonl. Always verify document_count/tribunal distribution LIVE via scripts/segmenter_governance_status.py and SegmenterDatasetStore.list_documents() before selecting a batch's candidates -- this backlog file's own numbers have repeatedly lagged real state between concurrent rounds (multiple independent sessions picked up the same next_move within the same day for batches 6-10, including batch9 and batch10 both hitting their own concurrency collisions independently); do not trust last_verified_run_id's snapshot without a live re-check, and expect another concurrent session to be working this same issue at any given moment. Before spawning an annotation subagent for a candidate, dedupe it correctly per risk class 9 below (content_hash(text) + (tribunal, id_documento)-vs-source_uri, NOT any externally-sourced hash field) -- batch10 wasted one full annotation round on two candidates that were already in the store because its first dedup pass compared the wrong hash space; batch9 independently hit the inverse shape (risk class 8: a selection-time content-hash dedup that can false-negative when a candidate needs HTML cleanup, since the store hashes cleaned text). After a dry-run ingest, always verify each returned document_id against the real store's documents/<id>.xml before writing for real. Tribunal-diversity mining is exhausted (only STM, TJAC, TJAM, TJAP, TJPE, TJSP, TRF1 remain without a usable candidate) -- the path forward is picking more unused Sentenca/Acordao candidates from already-represented tribunals, not chasing new ones; TRF6/TST still have unused candidates left over from batch9's scan. IMPORTANT for whichever mechanism picks this up next: knowledge/agent-runs/index.md and .claude/hourly-loop.md now declare the legacy AgentRun mechanism (this file's own historical updates, batches 1-5, 8, 9 and 10, came from that mechanism) deprecated in favor of a new Wisk runtime (.wisk/knowledge/) for the CausaGanha hourly loop -- batches 6 and 7 already ran under Wisk. A scheduled task whose stored prompt still hard-codes the legacy AgentRun scaffold as mandatory (as 83kr8s's, hv2ep2's and imy2ed's did) will keep conflicting with this policy until its owner updates it; this BacklogItem type is not itself named in the deprecation list (only AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck are), so it is kept updated here regardless of which mechanism a future round uses, but check .wisk/knowledge/ too before assuming this file alone is current. Budget for nine known defect/risk classes before trusting a batch's first pass -- see the numbered list below, including risk class 5 (a real production fix, already merged) and risk classes 7-9 (candidate-selection/concurrency process bugs, not production-code bugs)."
last_verified_run_id: "2026-09-16-exciting-mccarthy-imy2ed"
last_verified_at: "2026-09-16T15:20:00Z"
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

**Por que continua aberta:** o piso de RFC 0012 §5 item 4 (>=30 val,
>=30 teste, cada um adjudicado) continua exigindo algo perto de 200
documentos totais; estamos em 117 apos mesclar os lotes 9 e 10 (recheque
ao vivo antes de confiar neste número, dado o ritmo de rodadas
concorrentes neste mesmo dia). A mineração por diversidade de tribunal
está praticamente esgotada (restam apenas STM, TJAC, TJAM, TJAP, TJPE,
TJSP, TRF1 sem candidato usável) -- os lotes 6-10 confirmam que o
caminho daqui em diante é escolher mais candidatos não usados em
tribunais já representados, não perseguir tribunais novos.

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
