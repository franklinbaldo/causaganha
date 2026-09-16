---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Seven real batches now proven through scripts/ingest_djen_sample_technique1_batch.py: batch1 (round 0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs, 1 new tribunal (TJMS, a 25th tribunal surfaced by widening the candidate-length filter to 2500-18000 chars) + 3 more in already-represented tribunals; batch6 (a concurrent session driving the same issue in parallel via a different orchestration mechanism -- see note below -- merged first as PR #1549) 3 docs in TRF3/TJCE/TJMT targeting the 'preliminar' cue; batch7 (this round, 83kr8s, developed in parallel with batch6 under the same 'sixth batch' label before either had merged -- see note below) 8 docs, all in already-represented tribunals (TRF5, TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES) -- tribunal diversity is now confirmed exhausted (25 tribunals beyond TJRO, 26 total), document_count growth is the only remaining lever. document_count moved 61->68->74->81->86->93->96->104, val/test ceiling moved 9->10->11->12->13->14->16->16 -- still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents)."
unblock_condition: "Already unblocked and now has seven rounds of proof that the ingestion path scales without code changes. A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py toward ~200 total documents -- see docs/planning/evidence/segmenter-djen-sample-batch6-2026-09-16.json (this round's own before/after numbers, labeled batch6 in the evidence filename before the naming collision below was discovered) for the 93->101 delta this round produced in isolation; live document_count after merging with the concurrent PR #1549 is 104. Tribunal-diversity mining is exhausted (confirmed twice, by la7bsl and again by this round's live scan finding zero new tribunals under a 2500-18000 char filter) -- every future round should draw additional Sentenca/Acordao candidates from already-represented tribunals; a live scan this round found 250 more unused in-range candidates remaining after this batch (258 pre-batch minus 8 consumed), a large majority already XML-clean. Budget for the known defect/risk classes before trusting a batch's first pass: (1) dangling capitulo_merito/custas/honorarios/relatorio/ementa pairs with no closing cue in the source text -- every batch so far has needed at least one manually reviewed --allowed-unmatched-overrides entry (see docs/planning/evidence/segmenter-djen-sample-batch6-overrides.json for this round's 6 cases: all Juizado-Especial 'relatorio dispensado' sentencas with no closing cue, or short custas/honorarios clauses with no separate closing phrase -- confirm by inspecting the raw tagged text directly before declaring an override, per decision-accept-dangling-pairs-as-overrides in the 83kr8s run report, not by trusting the annotating subagent's own self-report); (2) some candidates' texto_limpo is NOT HTML-entity-decoded -- fix with html.unescape(); (3) some candidates' texto_limpo retains raw, sometimes-malformed embedded HTML markup that breaks the XML-based tagging pipeline -- always pre-check ET.fromstring(f'<text>{texto}</text>') before assigning to a subagent, reuse docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py; (4) a subagent can silently normalize a non-breaking space (U+00A0) to a regular space -- diff programmatically on any verbatim-fidelity skip, even when lengths already match; (5) CRLF-sourced candidates need line-ending normalization to LF before becoming a candidate, since XML's mandatory end-of-line normalization makes the existing verbatim-fidelity check structurally unable to preserve \\r\\n (batch5 finding). IMPORTANT for whichever mechanism picks this up next: knowledge/agent-runs/index.md and .claude/hourly-loop.md now declare the legacy AgentRun mechanism this file's own updates come from deprecated in favor of a new Wisk runtime (.wisk/knowledge/), discovered mid-round when PR #1549 (a concurrent Wisk-driven session working this same issue) merged to main first -- see decision-continue-under-legacy-mechanism-despite-deprecation in the 83kr8s run report for why this round finished under the legacy mechanism anyway. This BacklogItem type is not itself named in that deprecation (only AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck are), so it is kept updated here, but a future Wisk-driven round may track #1050's state in .wisk/knowledge/ instead -- check both locations before assuming this file is current."
last_verified_run_id: "2026-09-16-exciting-mccarthy-83kr8s"
last_verified_at: "2026-09-16T13:00:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Não está bloqueada. Sete rodadas reais já provaram o mecanismo de
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
- **Lote 4** (rodada mg2tp1): 5 documentos, 3 tribunais novos (TJSC,
  TRF4 x3, TRF6). `document_count` 81->86, teto de val/test 12->13
  (`docs/planning/evidence/segmenter-djen-sample-batch4-2026-09-16.json`).
- **Lote 5** (rodada la7bsl): 7 documentos, 1 tribunal novo (TJMS x4,
  25o tribunal, so visivel apos ampliar o filtro de tamanho para
  2500-18000 chars) + 3 em tribunais ja representados (TJPA x2, TJPI
  x1). `document_count` 86->93, teto de val/test 13->14
  (`docs/planning/evidence/segmenter-djen-sample-batch5-2026-09-16.json`).
- **Lote 6** (rodada concorrente, mecanismo Wisk, PR #1549 -- mesclada
  primeiro): 3 documentos em TRF3/TJCE/TJMT, visando a categoria mais
  rara (`preliminar`). Desenvolvida em paralelo a esta rodada sem
  coordenacao previa; ver nota IMPORTANTE em `unblock_condition` acima
  sobre a depreciacao do mecanismo legado descoberta por causa dessa
  colisao. `document_count` 93->96.
- **Lote 7** (esta rodada, 83kr8s -- desenvolvida em paralelo ao lote 6
  sob o mesmo rotulo "sexto lote" antes de qualquer uma mesclar; ver
  nota acima): 8 documentos, todos em tribunais ja representados (TRF5,
  TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES) -- diversidade de tribunal
  confirmada esgotada (nenhum tribunal novo no pool mesmo com filtro
  ampliado). `document_count` 93->101 em isolamento (arquivo de
  evidencia ainda rotulado `batch6` -- ver nota acima),
  104 apos merge com o lote 6 concorrente. Teto de val/test 14->16 (apos
  merge).
  (`docs/planning/evidence/segmenter-djen-sample-batch6-2026-09-16.json`).

**Por que continua aberta:** 25 tribunais além de TJRO já representados
(26 no total), mas o piso de RFC 0012 §5 item 4 (>=30 val, >=30 teste,
cada um adjudicado) continua exigindo algo perto de 200 documentos
totais. Diversidade de tribunal está confirmada esgotada no pool atual
(nenhum tribunal novo restante mesmo com filtro de 2500-18000 chars);
uma rodada futura minerando mais volume deve extrair candidatos
Sentenca/Acordao adicionais em tribunais já representados -- um scan ao
vivo desta rodada encontrou 250 candidatos nao usados restantes no
filtro apos este lote (258 antes do lote, menos 8 consumidos), a
maioria ja XML-limpa.

**Cinco classes de risco/defeito já mapeadas para o próximo lote:**

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
5. **Achado do lote 5**: candidatos com `texto_limpo` contendo quebras
   de linha CRLF (`\r\n`) quebram o check de fidelidade verbatim de
   forma estrutural — a normalização obrigatória de fim de linha da
   especificação XML (seção 2.11) torna `\r\n` irrecuperável pelo
   mecanismo de reconstrução existente independentemente da qualidade
   da anotação. Normalizar `texto_limpo` para LF antes de virar
   candidato, não pedir ao subagente para preservar CRLF.
6. **Achado do lote 6**: pares pendentes (`relatorio`/`capitulo_merito`/
   `custas`/`honorarios`) continuam a causa mais comum de falha na
   primeira passada (6 de 8 candidatos deste lote) — sempre confirmar
   pelo texto bruto (não pelo auto-relato do subagente) que o par
   realmente não tem cue de fechamento antes de declarar o override; as
   duas formas recorrentes são "relatório dispensado" em Juizado
   Especial e cláusulas curtas de custas/honorários sem frase de
   fechamento própria.
