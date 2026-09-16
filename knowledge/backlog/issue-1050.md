---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Two real batches now proven through scripts/ingest_djen_sample_technique1_batch.py: batch1 (round 0iuk22) ingested 7 documents across 7 tribunals; batch2 (this round, jyqinl) ingested 6 more across 6 further tribunals (TJPB, TJRN, TJRJ, TJMA, TJBA, TJRR), for 13/13 selected tribunals now represented beyond TJRO. document_count moved 68->74, val/test ceiling moved 10->11 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked and now has two rounds of proof that the ingestion path scales across tribunals without code changes. A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py (data/segmenter_samples/*.jsonl still holds ~800+ unused real candidates across ~25 remaining tribunals) toward ~200 total documents -- see docs/planning/evidence/segmenter-djen-sample-batch2-2026-09-16.json for this round's before/after numbers. Budget for two known annotation-defect classes before trusting a batch's first pass: (1) dangling capitulo_merito/custas/honorarios/relatorio pairs with no closing cue in the source text -- every batch so far has needed a manually reviewed --allowed-unmatched-overrides entry for at least some documents (see docs/planning/evidence/segmenter-djen-sample-batch2-overrides.json for this round's reasons); (2) some data/segmenter_samples/*.jsonl candidates' texto_limpo field is NOT HTML-entity-decoded -- it contains literal sequences like &Aacute;/&ccedil;/&nbsp; as raw text (confirmed live on TJTO id=285645419 and TJGO id=543565569, both dropped from batch2 after two failed redo attempts each). A future batch should either pre-decode texto_limpo (e.g. html.unescape) before building candidates.json -- checking whether that changes source_hash/content_hash expectations -- or give the annotation prompt an explicit worked example for escaping a literal source '&' as '&amp;' without decoding it, and should sample-check a candidate's texto_limpo for the '&[a-zA-Z]+;' pattern before assigning it to a subagent, to avoid burning a redo cycle discovering this after the fact."
last_verified_run_id: "2026-09-16-exciting-mccarthy-jyqinl"
last_verified_at: "2026-09-16T03:10:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Duas rodadas reais já provaram o mecanismo de
ingestão (`scripts/ingest_djen_sample_technique1_batch.py`) sem precisar
de nenhuma mudança de código entre elas:

- **Lote 1** (rodada 0iuk22): 7 documentos, 7 tribunais (TJMT, TJPA, TRF3,
  TJCE, TJES, TRF5, TJSE). `document_count` 61->68, teto de val/test 9->10.
- **Lote 2** (esta rodada, jyqinl): 6 documentos, 6 tribunais novos (TJPB,
  TJRN, TJRJ, TJMA, TJBA, TJRR). `document_count` 68->74, teto de val/test
  10->11
  (`docs/planning/evidence/segmenter-djen-sample-batch2-2026-09-16.json`).

**Por que continua aberta:** 13 tribunais além de TJRO já representados,
mas o piso de RFC 0012 §5 item 4 (>=30 val, >=30 teste, cada um
adjudicado) continua exigindo algo perto de 200 documentos totais. Ainda
há ~800+ candidatos reais não usados em `data/segmenter_samples/`, de
~25 tribunais restantes.

**Duas classes de risco já mapeadas para o próximo lote:**

1. Pares pendentes sem cue de fechamento (`capitulo_merito`/`custas`/
   `honorarios`/`relatorio`) — toda rodada até agora precisou de override
   manual revisado para pelo menos um documento
   (`docs/planning/evidence/segmenter-djen-sample-batch2-overrides.json`).
2. **Achado novo desta rodada**: alguns candidatos têm o campo
   `texto_limpo` com entidades HTML literais não decodificadas
   (`&Aacute;`, `&nbsp;`, etc. como texto puro, não como o caractere
   acentuado que deveriam representar). Confirmado ao vivo em TJTO
   (id=285645419) e TJGO (id=543565569) — ambos descartados desta rodada
   após duas tentativas de correção cada. Uma rodada futura deve checar
   o padrão `&[a-zA-Z]+;` no `texto_limpo` de um candidato antes de
   atribuí-lo a um subagente, e decidir entre pré-decodificar o campo ou
   instruir o prompt a escapar (não decodificar) um `&` literal da fonte.
