---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Three real batches now proven through scripts/ingest_djen_sample_technique1_batch.py: batch1 (round 0iuk22) ingested 7 documents across 7 tribunals; batch2 (round jyqinl) ingested 6 more across 6 further tribunals (TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR); batch3 (this round, uyx7xc) ingested 7 more across 7 further tribunals (TJGO, TJPI, TJMG, TJRS, TJTO, TRF2, TST), for 20/20 selected tribunals now represented beyond TJRO (21 total). document_count moved 61->68->74->81, val/test ceiling moved 9->10->11->12 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked and now has three rounds of proof that the ingestion path scales across tribunals without code changes. A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py (data/segmenter_samples/*.jsonl still holds real candidates across further remaining tribunals, though the easy/clean-text ones are increasingly used up) toward ~200 total documents -- see docs/planning/evidence/segmenter-djen-sample-batch3-2026-09-16.json for this round's before/after numbers. Budget for three known defect classes before trusting a batch's first pass: (1) dangling capitulo_merito/custas/honorarios/relatorio/ementa pairs with no closing cue in the source text -- every batch so far has needed a manually reviewed --allowed-unmatched-overrides entry for at least some documents (see docs/planning/evidence/segmenter-djen-sample-batch3-overrides.json for this round's reasons); (2) some candidates' texto_limpo is NOT HTML-entity-decoded (literal &Aacute;/&ccedil;/&nbsp; sequences) -- fix by applying html.unescape() to texto_limpo before building candidates.json (this round confirmed live that this cleanly recovers the exact TJTO document batch2 had dropped for this reason); (3) NEW this round: some candidates' texto_limpo retains raw, sometimes-malformed embedded HTML markup (a full <html><head>...<body><article> wrapper, and/or a stray unmatched </br> with no matching <br>) that breaks the XML-based tagging pipeline regardless of annotation quality -- confirmed by wrapping the RAW (untagged) candidate text in <text>...</text> and checking it parses as XML before ever assigning it to a subagent. A live scan of the full candidate pool found this affects ~37% of remaining candidates (114/483 with the full wrapper, 63/483 with the stray </br>) -- too large a fraction to keep dropping one-by-one. This round wrote and validated a small stdlib-only HTML-to-plain-text cleaner for this (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py) rather than dropping the affected candidates; a future round mining more candidates should reuse or promote this cleaner (it has no test suite yet, so it wasn't committed to scripts/) and should always pre-check a raw candidate's own XML-parseability before spending a subagent's annotation cycle on it."
last_verified_run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
last_verified_at: "2026-09-16T06:45:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Três rodadas reais já provaram o mecanismo de
ingestão (`scripts/ingest_djen_sample_technique1_batch.py`) sem precisar
de nenhuma mudança de código de produção entre elas:

- **Lote 1** (rodada 0iuk22): 7 documentos, 7 tribunais (TJMT, TJPA, TRF3,
  TJCE, TJES, TRF5, TJSE). `document_count` 61->68, teto de val/test 9->10.
- **Lote 2** (rodada jyqinl): 6 documentos, 6 tribunais novos (TJPB,
  TJRN, TJRJ, TJMA, TJBA, TJRR). `document_count` 68->74, teto de val/test
  10->11
  (`docs/planning/evidence/segmenter-djen-sample-batch2-2026-09-16.json`).
- **Lote 3** (esta rodada, uyx7xc): 7 documentos, 7 tribunais novos (TJGO,
  TJPI, TJMG, TJRS, TJTO, TRF2, TST). `document_count` 74->81, teto de
  val/test 11->12
  (`docs/planning/evidence/segmenter-djen-sample-batch3-2026-09-16.json`).

**Por que continua aberta:** 20 tribunais além de TJRO já representados
(21 no total), mas o piso de RFC 0012 §5 item 4 (>=30 val, >=30 teste,
cada um adjudicado) continua exigindo algo perto de 200 documentos
totais.

**Três classes de risco já mapeadas para o próximo lote:**

1. Pares pendentes sem cue de fechamento (`capitulo_merito`/`custas`/
   `honorarios`/`relatorio`/`ementa`) — toda rodada até agora precisou de
   override manual revisado para pelo menos um documento
   (`docs/planning/evidence/segmenter-djen-sample-batch3-overrides.json`).
2. Alguns candidatos têm o campo `texto_limpo` com entidades HTML
   literais não decodificadas (`&Aacute;`, `&nbsp;`, etc.). Esta rodada
   confirmou ao vivo que `html.unescape()` aplicado ao `texto_limpo`
   antes de montar `candidates.json` resolve isso por completo,
   inclusive no mesmo documento TJTO (id=285645419) que o lote 2 havia
   descartado por esse motivo.
3. **Achado novo desta rodada**: alguns candidatos têm `texto_limpo` com
   markup HTML bruto (às vezes malformado) embutido — um wrapper
   `<html><head>...<body><article>` completo, e/ou um `</br>` solto sem
   `<br>` correspondente — que quebra o parse XML do pipeline de
   anotação/ingestão independentemente da qualidade da anotação. Um scan
   ao vivo do pool completo de candidatos encontrou isso em ~37% dos
   candidatos restantes (114/483 com o wrapper completo, 63/483 com o
   `</br>` solto) — grande demais para descartar candidato por candidato.
   Em vez de descartar, esta rodada escreveu e validou um limpador
   HTML->texto puro só com biblioteca padrão
   (`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`)
   e recuperou os 5 candidatos afetados. Uma rodada futura minerando mais
   candidatos deve reusar ou promover esse limpador (ainda sem suite de
   testes própria, por isso não foi para `scripts/`) e sempre checar se o
   texto bruto do candidato já parseia como XML bem formado
   (`ET.fromstring(f"<text>{texto}</text>")`) antes de atribuí-lo a um
   subagente.
