---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Eight real batches now proven through scripts/ingest_djen_sample_technique1_batch.py, run under two alternating report mechanisms (legacy AgentRun scaffold and a new Wisk runtime) without needing a production-code change for most of them: batch1 (0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs (4 TJMS + 2 TJPA + 1 TJPI), first round to widen the candidate-length floor to 2500 chars and surface TJMS as a 25th tribunal; batch6 (Wisk round, PR #1549) 3 docs across TRF3/TJCE/TJMT (already-represented tribunals), targeting the 'preliminar' cue; batch7 (round zrek2s, PR #1553) 6 docs across TJRJ/TJGO/TJTO/TJPB/TJMA/TJRR, also targeting 'preliminar', and fixed a real production bug (see risk class 5 below); batch8 (this round, 83kr8s) 8 docs across TRF5/TJMT/TJRR/TJPA/TRF3/TJRJ/TJPB/TJES. Batches 6, 7 and 8 were all developed concurrently by independent sessions picking up the same 'grow the corpus' next_move at once, without coordination -- see the note on the AgentRun/Wisk mechanism split below and decision-continue-under-legacy-mechanism-despite-deprecation in the 83kr8s run report. document_count moved 61->68->74->81->86->93->96->102->109 (109 confirmed live after merging batch8 into the batch6+batch7 base -- one document shy of the naive 96+6+8=110 sum, most likely one candidate's exact source text had already been ingested by a concurrent batch and content-hash deduped to the same DocumentRecord id rather than adding a new one; harmless, not investigated further), val/test ceiling 16/16 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents) -- recheck scripts/segmenter_governance_status.py live rather than trusting any cached number in this file, including this one."
unblock_condition: "Already unblocked, eight rounds of proof the ingestion path scales without code changes (one real production bug found and fixed along the way by batch7 -- see risk class 5). A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py against the remaining pool in data/segmenter_samples/*.jsonl. Always verify document_count/tribunal distribution LIVE via scripts/segmenter_governance_status.py and SegmenterDatasetStore.list_documents() before selecting a batch's candidates -- this backlog file's own numbers have repeatedly lagged real state between concurrent rounds (three independent sessions picked up the same next_move within the same day for batches 6-8); do not trust last_verified_run_id's snapshot without a live re-check, and expect another concurrent session to be working this same issue at any given moment. Tribunal-diversity mining is exhausted (only STM, TJAC, TJAM, TJAP, TJPE, TJSP, TRF1 remain without a usable candidate) -- the path forward is picking more unused Sentenca/Acordao candidates from already-represented tribunals, not chasing new ones. IMPORTANT for whichever mechanism picks this up next: knowledge/agent-runs/index.md and .claude/hourly-loop.md now declare the legacy AgentRun mechanism (this file's own historical updates, batches 1-5 and 8, came from that mechanism) deprecated in favor of a new Wisk runtime (.wisk/knowledge/) for the CausaGanha hourly loop -- batches 6 and 7 already ran under Wisk. A scheduled task whose stored prompt still hard-codes the legacy AgentRun scaffold as mandatory (as 83kr8s's did) will keep conflicting with this policy until its owner updates it; this BacklogItem type is not itself named in the deprecation list (only AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck are), so it is kept updated here regardless of which mechanism a future round uses, but check .wisk/knowledge/ too before assuming this file alone is current. Budget for five known defect/risk classes before trusting a batch's first pass -- see the numbered list below, including risk class 5 (a real production fix, already merged)."
last_verified_run_id: "2026-09-16-exciting-mccarthy-83kr8s"
last_verified_at: "2026-09-16T12:15:00Z"
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

**Por que continua aberta:** o piso de RFC 0012 §5 item 4 (>=30 val,
>=30 teste, cada um adjudicado) continua exigindo algo perto de 200
documentos totais; estamos em 110 (recheque ao vivo antes de confiar
neste número, dado o ritmo de rodadas concorrentes neste mesmo dia). A
mineração por diversidade de tribunal está praticamente esgotada
(restam apenas STM, TJAC, TJAM, TJAP, TJPE, TJSP, TRF1 sem candidato
usável) -- os lotes 6, 7 e 8 confirmam que o caminho daqui em diante é
escolher mais candidatos não usados em tribunais já representados, não
perseguir tribunais novos.

**Cinco classes de risco/defeito já mapeadas para o próximo lote:**

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
