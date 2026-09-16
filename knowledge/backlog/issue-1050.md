---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Four real batches now proven through scripts/ingest_djen_sample_technique1_batch.py: batch1 (round 0iuk22) ingested 7 documents across 7 tribunals; batch2 (round jyqinl) ingested 6 more across 6 further tribunals (TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR); batch3 (round uyx7xc) ingested 7 more across 7 further tribunals (TJGO, TJPI, TJMG, TJRS, TJTO, TRF2, TST); batch4 (this round, mg2tp1) ingested 5 more across 3 further tribunals (TJSC, TRF4 x3, TRF6), for 23/23 selected tribunals now represented beyond TJRO (24 total). document_count moved 61->68->74->81->86, val/test ceiling moved 9->10->11->12->13 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents). Only 8 tribunals remain in the sample pool with no usable candidate yet (STM, TJAC, TJAM, TJAP, TJMS, TJPE, TJSP, TRF1) -- all previously and again this round confirmed to hold only 'Decisão'-type or sub-4000-char candidates, outside what the v7.1 guideline's document_type_hint covers."
unblock_condition: "Already unblocked and now has four rounds of proof that the ingestion path scales across tribunals without code changes. A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py toward ~200 total documents -- see docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json for this round's before/after numbers. New-tribunal diversity is nearly exhausted in the current sample pool (only 8 tribunals left, all without usable Sentenca/Acordao candidates) -- a future round mining more volume should widen the search past 'new tribunal only' and also pick additional, still-unused Sentenca/Acordao candidates from tribunals already represented (document_count growth, not just tribunal diversity, is what raises the RFC 0012 floor from here). Budget for four known defect/risk classes before trusting a batch's first pass: (1) dangling capitulo_merito/custas/honorarios/relatorio/ementa pairs with no closing cue in the source text -- every batch so far has needed a manually reviewed --allowed-unmatched-overrides entry for at least some documents (see docs/planning/evidence/segmenter-djen-sample-batch4-overrides.json for this round's reasons; this round's 3 dangling cases were all the same shape: a numbered-section 'capa+ementa-estruturada' export with no separate RELATORIO/VOTO to close the ementa against); (2) some candidates' texto_limpo is NOT HTML-entity-decoded -- fix by applying html.unescape() (or reuse the batch3 cleaner below, which decodes as a side effect of HTMLParser(convert_charrefs=True)); (3) some candidates' texto_limpo retains raw, sometimes-malformed embedded HTML markup that breaks the XML-based tagging pipeline regardless of annotation quality -- always pre-check a raw candidate's own XML-parseability (ET.fromstring(f'<text>{texto}</text>')) before assigning it to a subagent, and reuse docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py (reused unmodified again this round on all 5 batch4 candidates, all of which hit this exact defect) rather than writing a new cleaner; (4) NEW this round: a subagent can silently normalize a single non-breaking space (U+00A0) to a regular space during transcription -- caught by the ingestion script's own verbatim-fidelity check (reconstructed length matched source length exactly, 3977==3977, masking a same-length single-character substitution), confirmed by a programmatic char-by-char diff rather than eyeballing, and fixed by directly patching the one substring in the subagent's tagged output (safe here because the diff fell in plain text between tags, not near a tag boundary) rather than re-running the subagent -- a future round should diff programmatically on any verbatim-fidelity skip even when lengths already match, since a same-length substitution is invisible to a bare length check."
last_verified_run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
last_verified_at: "2026-09-16T06:45:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Quatro rodadas reais já provaram o mecanismo de
ingestão (`scripts/ingest_djen_sample_technique1_batch.py`) sem precisar
de nenhuma mudança de código de produção entre elas:

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
- **Lote 4** (esta rodada, mg2tp1): 5 documentos, 3 tribunais novos (TJSC,
  TRF4 x3, TRF6). `document_count` 81->86, teto de val/test 12->13
  (`docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json`).

**Por que continua aberta:** 23 tribunais além de TJRO já representados
(24 no total), mas o piso de RFC 0012 §5 item 4 (>=30 val, >=30 teste,
cada um adjudicado) continua exigindo algo perto de 200 documentos
totais. Restam apenas 8 tribunais no pool de amostras sem candidato
usável (STM, TJAC, TJAM, TJAP, TJMS, TJPE, TJSP, TRF1) -- diversidade de
tribunal está próxima do esgotamento no pool atual; uma rodada futura
minerando mais volume deve também considerar candidatos adicionais em
tribunais já representados, não só tribunais novos.

**Quatro classes de risco/defeito já mapeadas para o próximo lote:**

1. Pares pendentes sem cue de fechamento (`capitulo_merito`/`custas`/
   `honorarios`/`relatorio`/`ementa`) — toda rodada até agora precisou de
   override manual revisado para pelo menos um documento
   (`docs/planning/evidence/segmenter-djen-sample-batch4-overrides.json`
   para esta rodada; os 3 casos deste lote foram todos do mesmo formato:
   export "capa+ementa-estruturada" com seções numeradas, sem
   RELATORIO/VOTO separado para fechar a ementa).
2. Alguns candidatos têm o campo `texto_limpo` com entidades HTML
   literais não decodificadas (`&Aacute;`, `&nbsp;`, etc.) — resolvido
   por `html.unescape()` ou reusando o limpador do item 3 abaixo (que já
   decodifica como efeito colateral de `HTMLParser(convert_charrefs=True)`).
3. Alguns candidatos têm `texto_limpo` com markup HTML bruto (às vezes
   malformado) embutido — um wrapper `<html><head>...<body><article>`
   completo, e/ou um `</br>` solto sem `<br>` correspondente — que quebra
   o parse XML do pipeline de anotação/ingestão independentemente da
   qualidade da anotação. Sempre checar se o texto bruto do candidato já
   parseia como XML bem formado (`ET.fromstring(f"<text>{texto}</text>")`)
   antes de atribuí-lo a um subagente, e reusar
   `docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`
   (reusado sem alteração de novo nesta rodada, nos 5 candidatos do lote
   4, todos afetados por esse defeito) em vez de escrever um novo
   limpador.
4. **Achado novo desta rodada**: um subagente pode normalizar
   silenciosamente um espaço não separável (U+00A0) para espaço comum
   durante a transcrição — capturado pelo próprio check de fidelidade
   verbatim do script de ingestão, mas mascarado por um comprimento igual
   (3977==3977, uma substituição de mesmo tamanho é invisível a um check
   de comprimento simples). Descoberto via diff caractere-a-caractere
   programático, não inspeção visual, e corrigido reescrevendo o único
   trecho afetado no arquivo do subagente (seguro aqui porque o diff caiu
   em texto simples entre tags, não perto de um limite de tag) em vez de
   rodar o subagente de novo. Uma rodada futura deve sempre diffar
   programaticamente qualquer skip por fidelidade verbatim, mesmo quando
   os comprimentos já batem.
