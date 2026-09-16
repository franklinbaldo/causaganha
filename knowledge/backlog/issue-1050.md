---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Seven real batches now proven through scripts/ingest_djen_sample_technique1_batch.py, run under two alternating report mechanisms (AgentRun scaffold and Wisk) without any production-code change between most of them: batch1 (0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs (4 TJMS + 2 TJPA + 1 TJPI), first round to widen the candidate-mining length floor to 2500 chars and surface TJMS as a 25th tribunal; batch6 (Wisk round, PR #1549) 3 docs across TRF3/TJCE/TJMT/TJPB (already-represented tribunals, targeting the 'preliminar' cue); batch7 (zrek2s) 6 docs across TJRJ/TJGO/TJTO/TJPB/TJMA/TJRR, also targeting 'preliminar'. document_count moved 61->68->74->81->86->93->96->102, val/test ceiling moved 9->10->11->12->13->14->14->15 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents). Tribunal-diversity mining is exhausted for the remaining 7 tribunals in the sample pool (STM, TJAC, TJAM, TJAP, TJPE, TJSP, TRF1 -- TJMS was surfaced by batch5's wider length floor and is no longer in this list); batches 6-7 confirm the path forward is picking more unused candidates from already-represented tribunals, not chasing new ones."
unblock_condition: "Already unblocked, seven rounds of proof the ingestion path scales without code changes (one production bug found and fixed along the way -- see risk class 5 below). A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py against the remaining pool (~220 unused, in-range real Sentença/Acórdão candidates confirmed live as of batch7 in data/segmenter_samples/*.jsonl, 79 of them with a 'preliminar' cue hit -- still the corpus's scarcest category at ~22/22 instances after batch7). Always verify document_count/tribunal distribution LIVE via scripts/segmenter_governance_status.py and SegmenterDatasetStore.list_documents() before selecting a batch's candidates -- this backlog file's own numbers lag real state between rounds (confirmed stale for batches 5-6 as of batch7; do not trust last_verified_run_id's snapshot without a live re-check). Budget for five known defect/risk classes before trusting a batch's first pass: (1) dangling capitulo_merito/custas/honorarios/relatorio/ementa pairs with no closing cue in the source text -- every batch so far has needed reviewed --allowed-unmatched-overrides entries (see docs/planning/evidence/segmenter-djen-sample-batch7-overrides.json for this round's 4 documents/7 categories; the recurring shape is custas+honorarios sharing one dispositivo sentence with no separate closing cue for either, or a capa+ementa-estruturada export with no RELATORIO/VOTO to close ementa/relatorio against); (2) texto_limpo with undecoded HTML entities -- html.unescape(); (3) texto_limpo with raw/malformed embedded HTML markup breaking XML parsing -- pre-check ET.fromstring(f'<text>{texto}</text>') and reuse docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py; (4) a same-length single-character substitution (e.g. NBSP->space) that verbatim-fidelity's length check alone won't catch -- diff programmatically; (5) FIXED IN PRODUCTION CODE this round (batch7): scripts/ingest_djen_sample_technique1_batch.py's _parse_tagged called tagged_text.strip() before XML-wrapping, and Python's str.strip() treats U+00A0 (non-breaking space) as whitespace -- a source document whose texto_limpo genuinely opens/closes with NBSP had that content silently dropped, producing a false verbatim-fidelity mismatch. Fixed to tagged_text.strip('\\n\\r\\t ') (ASCII-only), with a regression test (test_ingest_preserves_leading_nbsp_and_blank_lines) -- future batches no longer need to work around this by hand. Also watch for scripts/segmenter_semantic_audit.py's *_collapsed heuristic flagging a genuinely-correct single tag as a false positive when the same figure/citation is repeated in narrative text before the operative tag (documented, expected shape -- see tests/segmenter_dataset/test_segmenter_audit_scripts.py's allowlist; verify each new finding against source text before extending it, never silence the assertion)."
last_verified_run_id: "2026-09-16-exciting-mccarthy-zrek2s"
last_verified_at: "2026-09-16T12:15:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Sete rodadas reais já provaram o mecanismo de
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
  (TRF3, TJCE, TJMT, TJPB -- tribunais já representados), visando a
  categoria mais rara (`preliminar`). `document_count` 93->96. Primeira
  rodada desta linhagem a rodar sob o mecanismo Wisk em vez do scaffold
  AgentRun -- confirma que os dois mecanismos agora se alternam na mesma
  linhagem de issue.
- **Lote 7** (rodada zrek2s): 6 documentos (TJRJ, TJGO, TJTO, TJPB, TJMA,
  TJRR), também visando `preliminar`. `document_count` 96->102, teto de
  val/test 14->15
  (`docs/planning/evidence/segmenter-djen-sample-batch7-2026-09-16.json`).
  Encontrou e corrigiu no código de produção um defeito novo (ver classe
  5 abaixo) e estendeu a allowlist de falsos positivos do audit semântico
  com uma verificação real contra o texto-fonte.

**Por que continua aberta:** o piso de RFC 0012 §5 item 4 (>=30 val,
>=30 teste, cada um adjudicado) continua exigindo algo perto de 200
documentos totais; estamos em 102. Restam ~220 candidatos reais e nunca
usados no pool (`data/segmenter_samples/*.jsonl`, verificado ao vivo pelo
lote 7), 79 deles com hit heurístico para `preliminar` (ainda a
categoria mais rara do corpus). A mineração por diversidade de tribunal
está praticamente esgotada (restam apenas STM, TJAC, TJAM, TJAP, TJPE,
TJSP, TRF1 sem candidato usável) -- os lotes 6 e 7 confirmam que o
caminho daqui em diante é escolher mais candidatos não usados em
tribunais já representados, não perseguir tribunais novos.

**Cinco classes de risco/defeito já mapeadas para o próximo lote:**

1. Pares pendentes sem cue de fechamento (`capitulo_merito`/`custas`/
   `honorarios`/`relatorio`/`ementa`) — toda rodada até agora precisou de
   override manual revisado para pelo menos um documento
   (`docs/planning/evidence/segmenter-djen-sample-batch7-overrides.json`
   para os 4 documentos/7 categorias desta rodada; o formato recorrente é
   `custas`+`honorarios` dividindo uma única frase do dispositivo sem cue
   de fechamento separado para nenhum dos dois, ou um export
   "capa+ementa-estruturada" sem RELATORIO/VOTO para fechar
   `ementa`/`relatorio`).
2. Alguns candidatos têm o campo `texto_limpo` com entidades HTML
   literais não decodificadas — resolvido por `html.unescape()`.
3. Alguns candidatos têm `texto_limpo` com markup HTML bruto (às vezes
   malformado) embutido — checar `ET.fromstring(f"<text>{texto}</text>")`
   antes de atribuir a um subagente e reusar
   `docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`.
4. Uma substituição de mesmo comprimento (ex.: NBSP->espaço comum) que o
   check de comprimento da fidelidade verbatim sozinho não pega — diffar
   programaticamente.
5. **CORRIGIDO NO CÓDIGO DE PRODUÇÃO nesta rodada (lote 7)**:
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
