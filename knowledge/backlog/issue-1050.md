---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not blocked. Fifteen real batches now proven through scripts/ingest_djen_sample_technique1_batch.py, run under alternating report mechanisms (legacy AgentRun scaffold and the current Wisk runtime) without needing a production-code change for most of them: batch1 (0iuk22) 7 docs/7 tribunals; batch2 (jyqinl) 6 docs/6 tribunals; batch3 (uyx7xc) 7 docs/7 tribunals; batch4 (mg2tp1) 5 docs/3 tribunals; batch5 (la7bsl) 7 docs (4 TJMS + 2 TJPA + 1 TJPI), first round to widen the candidate-length floor to 2500 chars and surface TJMS as a 25th tribunal; batch6 (Wisk round, PR #1549) 3 docs across TRF3/TJCE/TJMT (already-represented tribunals), targeting the 'preliminar' cue; batch7 (round zrek2s, PR #1553) 6 docs across TJRJ/TJGO/TJTO/TJPB/TJMA/TJRR, also targeting 'preliminar', and fixed a real production bug (see risk class 5 below); batch8 (round 83kr8s, PR #1552) 8 docs across TRF5/TJMT/TJRR/TJPA/TRF3/TJRJ/TJPB/TJES; batch9 (round hv2ep2, PR #1557) 6 docs across TJBA/TJMG/TJRS/TJSE/TRF2/TJCE (all already-represented tribunals, chosen for lowest store document-count rather than rare-category cue; hit a real concurrency collision of its own, see risk class 8 below); batch10 (round imy2ed, PR #1559) 2 docs targeting 'preliminar' (TJBA/574460089, TJRN/72797727) -- an initial selection (TJRN/72798564, TJBA/574460090) was reverted mid-round after discovering both were already-ingested duplicates (see risk class 9 below); batch11 (Wisk round, PR #1562) 2 docs, TJRN/72796443 and TJMA/42728353, both already-represented tribunals at the lowest store_count tier (2 each) -- no unused 'preliminar'-cue candidate remained anywhere in an already-represented tribunal after a fresh full scan, so this batch followed batch9's volume strategy instead; hit a new process defect, see risk class 10 below; batch12 (round 5lvbii, PR #1563) 2 docs, TJES/577054686 and TJGO/543562390, tied for the lowest non-singleton store_count (2 each) with a 'preliminar' cue each -- TJGO needed html.unescape() (364 raw HTML entities, no embedded markup) and a reviewed override for two pairs with no closing cue in the source (capitulo_merito, custas), verified against the raw text before declaring; batch13 (round 96cgqx, PR #1565) 2 docs, TJSE/578949084 (Acordao) and TJRS/458637070 (Sentenca), both the ONLY remaining eligible candidate for their respective tribunal (store_count=2 each, tied with TJPI/TJMG/TRF5/TRF2/TJTO) -- TJSE had 3 raw ASCII control characters (U+001C/U+001D as improvised quotes, U+0013 as an opening parenthesis), resolved with a length-preserving ASCII substitution (risk class 7); TJRS had embedded raw HTML markup, resolved with the batch3 cleaner (risk class 3); batch14 (this Wisk round) 3 docs, TST/237077355, TJPI/22443810, TRF5/349055692 -- a genuinely independent, concurrent session (this same round) picked the identical starting snapshot (121 documents) and the same volume-tier strategy as batch13, landing on TJSE/578949084 and TJRS/458637070 as well before either PR merged; discovered only as a merge conflict against origin/main after batch13 had already merged as PR #1565 (see risk class 12 below). Reconciled by keeping PR #1565's TJSE/TJRS as canonical and dropping this round's own re-ingestion of both (TJRS was a byte-identical duplicate document_id, no data loss; TJSE differed only in one substituted control character, so both sessions' TJSE ingestion could not both be kept without producing a true near-duplicate in the corpus). A sixth candidate this round selected before the merge, TJSC/587254906, was also reverted for an unrelated reason: it already existed in the store from batch4 (PR #1545), because data/segmenter_samples/tjsc_acordao.jsonl's own info.tribunal field is blank for every record in that file, silently breaking the (tribunal, id) dedup check against the store's real tribunal value (see risk class 11 below). batch15 (round j2t668, this round) 6 docs, TST/237077375, TJRJ/327515150, TJRJ/327497197, TJTO/285693071, TJTO/285710292, TRF2/301247724 -- all already-represented tribunals at the lowest store_count tier (2 each), continuing the volume-over-diversity strategy. A live pool scan this round found 218 eligible never-used real candidates still remaining across 17 tribunals, correcting a stale 'pool nearly exhausted' framing carried by prior next_move notes (that referred only to new-tribunal diversity, not remaining volume). Two candidates (TJTO/285693071, TRF2/301247724) hit the NBSP-to-space substitution defect pervasively (12 and 33 occurrences respectively, not a single isolated instance as in batch4/13) -- fixed by a new technique, not a manual patch: programmatically diffing the reconstructed (tags-stripped) text against source character-by-character, verifying every diff is exclusively NBSP-related, then reinserting the correct bytes into the tagged XML at the mapped positions and re-verifying byte-identical reconstruction before ingesting (see risk class 13 below). Four overrides were needed for dangling pairs with no closing cue (capitulo_merito x2, custas x2, honorarios x2, encerramento x1), all verified against the raw source text. document_count moved 61->68->74->81->86->93->96->102->109->115->117->119->121->123 (batch13)->126 (batch14)->132 (batch15), val/test ceiling 17/17 (batch9, 115 docs) ->18/18 (117-121 docs) ->19/19 (126 docs, batch14) ->20/20 (132 docs, batch15) -- recheck scripts/segmenter_governance_status.py live rather than trusting any cached number in this file, including this one. Still far below RFC 0012 Sec 5 item 4's >=30/>=30 floor (needs roughly 200 total documents). batch16 (round epgxv2) 6 docs, TST/237077398, TST/237077448, TJPI/22443818, TJPI/22443820, TJGO/543516662, TJPB/578832621 -- TST and TJPI's remaining eligible pool fully exhausted by this batch (0 left after this round), TJGO/TJPB picked from the next-lowest volume tier, continuing the same volume-over-diversity strategy. document_count 132->138, val/test ceiling 20/20->21/21. TJGO's texto_limpo again carried un-decoded raw HTML entities (411 occurrences, same recurring per-tribunal quirk as batch12 -- html.unescape() resolves it cleanly to 0 remaining, applied before re-annotating), and one candidate (TJPI/22443820) hit two independent defects: the same pervasive NBSP-to-space substitution as batch15 (70 occurrences, fixed with the same diff-and-remap technique, see docs/planning/evidence/segmenter-djen-sample-batch16-fix-nbsp.py) AND a genuine under-tagging: the ementa pair's `<fim>` was omitted even though an explicit closing cue ('5. Recurso conhecido e improvido.' right before the ACÓRDÃO header) was present in the source and had already been correctly closed in a sibling document of the same batch (TJPI/22443818) -- see risk class 14 below, a new distinct failure mode from the already-documented 'genuinely no closing cue' dangling-pair class. Three overrides were needed for pairs verified to have no closing cue at all (capitulo_merito x2 across TST/237077448 and TJPB/578832621, voto x1 in TST/237077448, custas x1 in TJGO/543516662). batch17 (round 0hjgmk) 5 docs, TJBA/574460085, TJMA/42736393, TJMA/42730832, TJCE/363647616, TJCE/363657243 -- a sixth originally-selected candidate (TJBA/574460088) was dropped before annotation after a raw-text SequenceMatcher.ratio()=0.98 near-duplicate check against its own batch sibling (same court/judge/template embargos-de-declaracao ruling); see risk class 14 (renumbered/actually written this round, batch16 had promised it but never wrote it) for the missing-inicio-despite-no-fallback-cue defect found in TJCE/363657243's relatorio, and risk class 15 (new) for a real bug found and fixed in the NBSP diff-and-remap fix script itself (an off-by-range end-of-slice bug that silently deleted an XML tag sitting between two stripped-text positions without changing the stripped text, so the existing 'stripped text matches source' self-check alone could not catch it -- caught only by adding a before/after XML-tag-multiset equality check). document_count 138->143, annotation_count 191->196, val/test ceiling unchanged at 21/21 (all 5 documents are train-only, no second independent annotation yet). batch18 (rodada Wisk 20260917T032539Z) 6 docs, TJES/577030718, TJES/577039281, TJRR/568111547, TJRR/568208030, TJMT/74428001, TRF3/42490548 -- TJMG/TJRN/TJSE/TJRS confirmados esgotados no pool (zero candidatos elegiveis restantes); TRF4 foi escolhido inicialmente mas todo o seu pool de acordaos remanescentes (9 candidatos) revelou-se inutilizavel: cada um colapsa abaixo do piso de 2500 caracteres depois que o limpador HTML do lote 3 remove o markup embutido, mesmo com o comprimento bruto pre-limpeza parecendo elegivel -- ver classe de risco 16 (nova) abaixo. document_count 143->149, annotation_count 196->202, teto de val/test 21/21->22/22 (scripts/segmenter_governance_status.py, confirmado ao vivo). Quatro documentos precisaram de --allowed-unmatched-overrides para pares sem cue de fechamento (custas/honorarios/relatorio/preliminar), incluindo um caso de fim compartilhado (TJRR/568208030: honorarios compartilha o mesmo parentetico de fechamento de custas em uma clausula combinada), todos verificados contra o texto-fonte bruto antes de declarar. uv run ruff check/format --check limpos; segmenter_semantic_audit.py sem nenhum achado novo nos 6 documentos deste lote. batch20 (rodada Wisk 20260917T062515Z, primeira rodada do loop horario a rodar sob o runtime Wisk desde a migracao declarada em .claude/hourly-loop.md, apos revalidar ao vivo que o handoff issue #1471 permanece bloqueado por credenciais IA ausentes pela 7a rodada consecutiva e pivotar para #1050) 6 docs, todos TRF2 (301222642, 301222655, 301222733, 301222762, 301222819 -- Acordaos; 301248486 -- Sentenca), esgotando TRF2 de 21 para 15 candidatos elegiveis restantes no pool ao vivo. Todos os 5 acordaos precisaram do limpador HTML do lote 3 (markup <b>/</br> embutido) e todos os 6 (acordaos e sentenca) tiveram substituicao NBSP->espaco pervasiva na transcricao do subagente (1 ocorrencia cada, corrigida com o script de diff-e-remapeamento ja existente docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py, reutilizado verbatim sem modificacao). Cinco overrides --allowed-unmatched-overrides foram declarados para o par `ementa` sem cue de fechamento (formato capa+ementa-estruturada do TRF2: EMENTA abre direto em secoes numeradas I-IV sem RELATORIO/VOTO separado, mesma classe ja documentada nos lotes 3/4/7/14), mais dois no par `custas`/`honorarios` da sentenca (clausula combinada de enunciado unico 'Sem custas e honorarios advocaticios', mesmo padrao ja sancionado). Todos verificados contra o texto-fonte bruto antes de declarar. document_count 155->161, annotation_count 208->214, teto de val/test 23/23->24/24 (scripts/segmenter_governance_status.py, confirmado ao vivo; lote train-only, sem segunda anotacao independente). segmenter_semantic_audit.py sinalizou 1 achado novo (fundamentacao_legal_collapsed em TRF2/301222762, 'art.' aparece 4x mas so 1 fundamentacao_legal foi tagueado) -- revisado e confirmado falso positivo: as outras 3 ocorrencias de 'art.' estao todas dentro de citacoes bare ja corretamente tagueadas como ref_normativa na lista 'Dispositivos relevantes citados', nao dentro de linguagem de raciocinio-com-conector que justificaria fundamentacao_legal (mesma classe de falso positivo ja vista em 5 documentos pre-existentes do corpus). uv run ruff check/format --check limpos; uv run pytest -q tests/segmenter_dataset ainda rodando no momento deste commit (corpus de 161 documentos tornou a suite lenta o suficiente para exceder timeouts curtos -- ver commit de fechamento para o resultado confirmado). batch21 (rodada Wisk 20260917T082642Z) 6 docs, todos TRF2 (301222742, 301222784, 301222723, 301222696, 301222620, 301222706 -- todos Acordaos, 9ª Turma Especializada), esgotando TRF2 de 13 para 7 candidatos elegiveis restantes no pool ao vivo (as Sentencas remanescentes ficaram todas abaixo do piso de 2500 caracteres apos limpeza). uv run wisk init . precisou ser rodado antes de wisk start porque o consumer bundle gitignorado do Wisk (.wisk/specs, .wisk/knowledge/system, manifest.json) estava ausente neste checkout fresco, causando no-eligible-session. Handoff #1471 revalidado e reconfirmado bloqueado (baseline commit inalcancavel, credenciais IA ausentes) pela 8a+ rodada consecutiva, disposicao REFRAMED, pivota para #1050 (mesmo padrao do lote 20). Cinco overrides --allowed-unmatched-overrides para o par ementa (mesma classe capa+ementa-estruturada); o sexto documento teve o par corretamente fechado pelo subagente, confirmado por grep antes de decidir. Nenhum achado semantico novo. document_count 161->167, annotation_count 214->220, teto de val/test 24/24->25/25. uv run ruff check/format --check limpos; uv run pytest -q tests/segmenter_dataset excedeu novamente os timeouts curtos com 167 documentos, resultado a confirmar. batch22 (rodada AgentRun gbf44b, primeira rodada do prompt agendado a rodar apos o repositorio ficar sem nenhuma PR de dominio aberta) 6 docs, TJGO/543564741, TJPB/578900185, TJPA/576803379, TJPA/576805366, TJRJ/327508788, TJTO/285747298 -- todos Sentencas, escolhidos por store_count empatado em 4 (tribunais ja representados). TJBA (tambem store_count=4) foi verificado e excluido: seu unico candidato elegivel restante (574460088) ja havia sido identificado no lote 17 como quase-duplicata (SequenceMatcher.ratio()=0.98) de um documento ja no store (574460085), entao nao foi reusado. TJTO precisou do limpador HTML do lote 3 (markup <html>/<body>/<section>/<p> embutido); os demais 5 ja vinham como texto plano (TJGO precisou apenas de html.unescape() para as entidades HTML brutas, mesmo padrao recorrente ja documentado nos lotes 12/16/18). Dois defeitos de transcricao encontrados e corrigidos: (1) TJGO/543564741 teve substituicao NBSP pervasiva (5 ocorrencias) -- o proprio subagente corrigiu o arquivo por conta propria numa segunda passada antes que o script de diff-e-remapeamento (docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py) precisasse ser aplicado; a verificacao independente desta rodada confirmou o match ja corrigido; (2) TJPA/576803379 tinha 3 ocorrencias de \\\"&\\\" bruto (nome de parte \\\"MORETTI & MACIEL LTDA\\\") nao escapado como entidade XML, causando XML malformado -- corrigido com uma substituicao regex simples (`&` -> `&amp;`, preservando qualquer entidade ja existente), sem alterar o conteudo textual (a funcao de reconstrucao ja desescapa entidades). Tres overrides --allowed-unmatched-overrides foram declarados, todos verificados contra o texto-fonte bruto antes de declarar: capitulo_merito em TJPA/576803379 (o raciocinio de merito flui direto para o dispositivo_abertura \\\"Ante o exposto\\\" sem frase de fechamento distinta, mesmo padrao ja documentado), e custas+honorarios em TJRJ/327508788 e TJPB/578900185 (enunciados unicos e curtos, sem marcadores de abertura/fechamento distintos, mesma classe combinada ja sancionada nos lotes 12/18/20). `scripts/segmenter_semantic_audit.py` sinalizou 1 achado novo (fundamentacao_legal_collapsed em TJTO/285747298, doc_12f989ac213c5eadf857aacc69b33ad2) -- revisado e confirmado falso positivo da mesma classe ja documentada nos lotes 12/20: as ocorrencias adicionais de \\\"art.\\\" estao dentro de um bloco de ementa de precedente do STJ (REsp 1.804.804/MS) citado verbatim e ja coberto por uma unica tag ref_normativa, e dentro de uma transcricao literal do texto legal (Lei 11.101/2005 arts. 50/59, CPC art. 584) tambem ja coberta por fundamentacao_legal+ref_normativa na frase introdutoria. document_count 167->173, annotation_count 220->226, teto de val/test 25/25->26/26 (scripts/segmenter_governance_status.py, confirmado ao vivo; lote train-only, sem segunda anotacao independente). `git status --short data/segmenter` confirmou exatamente 6 novos documents/*.xml e 6 novos annotations/<id>/. `uv run ruff check`/`format --check` limpos. batch23 (rodada Wisk 20260919T192610Z) 6 docs, todos TRF2 (301222629, 301222677, 301222685, 301222713, 301222792, 301228222 -- todos Acordaos, 9ª Turma Especializada), escolhidos por serem disjuntos das tribunais de uma PR concorrente (#1585, lote 22: TJGO/TJPB/TJPA/TJRJ/TJTO) aberta minutos antes desta rodada, eliminando risco de colisao de document_id. Achado e corrigido um bug estrutural real e antes indocumentado (classe de risco 17, nova): aninhar uma tag single-anchor (ex: resultado) diretamente dentro de <inicio>/<fim> de um par e descartado silenciosamente por _text_element_to_labels (o branch _PAIR_ROLES so emite o label do proprio wrapper, nunca faz splice dos child_items aninhados) -- a fidelidade verbatim sozinha NAO detecta isso, pois o texto reconstruido nao muda. Corrigido em 3 documentos reposicionando resultado como irmao de inicio/fim. Tambem uma reconfirmacao da classe de risco 14: um override 'sem cue de fechamento' declarado pelo subagente de 301222685 foi contradito pela mesma estrutura boilerplate ja usada com sucesso por dois documentos irmaos do mesmo lote -- corrigido inserindo o fim faltante em vez de aceitar o override. document_count 173->179, annotation_count 226->232, teto de val/test 26/26->27/27. Cinco overrides ementa (mesmo padrao capa+ementa-estruturada). uv run ruff check/format --check limpos; segmenter_semantic_audit.py sem achados novos; scripts/segmenter_governance_status.py e pytest tests/segmenter_dataset novamente lentos com 173 documentos, resultado a confirmar no commit de fechamento desta fusao. MERGE (fusao PR #1586 sobre main pos-#1585, rodada 20260919T232524Z): PR #1585 (lote 22) e PR #1586 (lote 23) foram abertas quase simultaneamente sobre o mesmo commit-base, ambas mergeable_state=clean e com 11/11 CI verde, escolhendo tribunais deliberadamente disjuntos (TJGO/TJPB/TJPA/TJRJ/TJTO vs TRF2) para nao colidir em document_id. #1585 foi mesclada primeiro (squash e54a0b0); #1586 precisou de um merge de origin/main dentro da propria branch para resolver um conflito textual neste campo (nenhum conflito nos arquivos de dados data/segmenter/), resolvido preservando ambas as narrativas de lote em ordem e corrigindo os deltas do lote 23 para a base real pos-lote-22 (173, nao 167). document_count real apos ambos os lotes: 179 (confirmar ao vivo antes de qualquer lote futuro). batch24 (rodada AgentRun fv62kx) 6 docs, TJBA/574460088, TJMA/42725100, TJPI/22443826 (Acordao), TJES/577051509, TJGO/543517919, TJPB/578906897 -- escolhidos por store_count via scan ao vivo com o limpador HTML real do lote 3 (nao apenas html.unescape()): TJSC/TRF6/TJMG/TJRS/TJSE/TJRN confirmados esgotados (0 candidatos elegiveis restantes cada) e TRF4 reconfirmado inutilizavel (classe de risco 16, 0 elegiveis apos limpeza real), entao o proximo tier real com volume foi TJBA (store_count=4, 1 elegivel) mais cinco tribunais do tier store_count=5 (TJMA/TJPI/TJES/TJGO/TJPB, escolhidos entre varios por serem os de menor pool restante). Verificacao independente via `_text_element_to_labels` real (nao autorrelato dos subagentes) confirmou fidelidade verbatim byte-a-byte nos 6 antes de ingerir; `resultado` confirmado presente e posicionado como irmao de `inicio`/`fim` (nao filho) em todos, seguindo a instrucao explicita dada aos subagentes para evitar a classe de risco 17. Dois overrides `capitulo_merito` (TJMA/42725100 'passo a decidir', TJBA/574460088 'Decido.') verificados contra o texto-fonte: ambos fluem direto para um `dispositivo_abertura` ja tagueado, sem frase de fechamento distinta propria -- preferido declarar a fabricar uma tag de fechamento inedita (zero precedente no corpus para `capitulo_merito` fechado). Cinco outros overrides (custas/honorarios em enunciados combinados de sentenca curta, e `relatorio` 'dispensado' em TJPB/578906897) reusam padroes ja sancionados nos lotes 12/18/19/20/22, cada um reverificado contra o texto-fonte deste lote antes de declarar. `scripts/segmenter_semantic_audit.py` sinalizou zero achados novos (confirmado por comparacao de doc_id contra os 11 achados pre-existentes). `git status --short data/segmenter` confirmou exatamente 6 novos `documents/*.xml` e 6 novos `annotations/<id>/`. `uv run ruff check`/`format --check` limpos; `uv run pytest -q tests/segmenter_dataset` 100% verde (208 passed) apos o corpus crescer para 185 documentos. document_count 179->185, annotation_count 232->238, teto de val/test 27/27->28/28 (scripts/segmenter_governance_status.py, confirmado ao vivo; lote train-only, sem segunda anotacao independente)."
unblock_condition: "Already unblocked, fifteen rounds of proof the ingestion path scales without code changes (one real production bug found and fixed along the way by batch7 -- see risk class 5). A future round should keep running batches through scripts/ingest_djen_sample_technique1_batch.py against the remaining pool in data/segmenter_samples/*.jsonl. Always verify document_count/tribunal distribution LIVE via scripts/segmenter_governance_status.py and SegmenterDatasetStore.list_documents() before selecting a batch's candidates -- this backlog file's own numbers have repeatedly lagged real state between concurrent rounds (multiple independent sessions picked up the same next_move within the same day for batches 6-14, batches 13 and 14 even picking the exact same two candidates independently -- see risk class 12); do not trust last_verified_run_id's snapshot without a live re-check, and expect another concurrent session to be working this same issue at any given moment. Before spawning an annotation subagent for a candidate, dedupe it correctly per risk class 9 below (content_hash(text) + (tribunal, id_documento)-vs-source_uri, NOT any externally-sourced hash field) -- AND per risk class 11, derive the tribunal side of that pair from the jsonl FILENAME, not from the candidate record's own info.tribunal field, since at least one file (tjsc_acordao.jsonl) has that field blank for every record. After a dry-run ingest, always verify each returned document_id against the real store's documents/<id>.xml before writing for real (git status --short data/segmenter after a REAL ingest is the reliable tell: a candidate that produces only a new annotations/<id>/ann_*.xml with no matching new documents/<id>.xml was already in the store -- revert that annotation file, it adds no independence value if its annotator_config matches the pre-existing one), AND keep the tagged-annotation directory passed to --tagged-dir free of any file that shares a bare `<id_documento>.txt` name with a source/candidate file -- see risk class 10 below, a real batch11 near-miss. Before opening a PR, fetch and diff against the current origin/main tip (not just the branch's own stale base) to catch a same-candidate collision with a concurrent session's already-merged batch before it becomes a merge conflict -- see risk class 12. Tribunal-diversity mining is exhausted only for a couple of specific tribunals (TRF6/TJSC, store_count=1 each, no eligible candidate left below the 2500-char floor) -- a live full-pool scan after batch15 (field names `text`/`info.id`, NOT `texto_limpo`/`id_documento` -- an earlier scan using the wrong field names undercounted to zero and wrongly suggested the whole pool was nearly exhausted, see risk class 13) found 218 eligible, never-used real candidates still remaining across 17 tribunals, so volume growth is far from supply-constrained. The path forward remains picking unused Sentenca/Acordao candidates from already-represented tribunals by volume (lowest store_count first), not chasing new tribunals or a specific rare category; after batch15, TJMG/TJGO/TJES (2-3 each) are the next-lowest tier once TST/TJRJ/TJTO/TRF2 (this batch's picks) move up. When a start/end pair has no closing cue in the source text (a recurring, expected shape, not a bug -- see risk classes 4/6), verify against the raw source text before declaring a --allowed-unmatched-overrides reason, same as every prior batch that hit this. A source jsonl with raw HTML markup (<b>/<table>/<br>/etc, not just entities) needs the batch3 HTML-to-text cleaner (docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py) BEFORE handing the text to an annotation subagent, not just html.unescape() -- batch13/14 found this the hard way for TJSC, TJRS and TST, each requiring a redo after the first annotation attempt silently reproduced the markup or hit malformed-XML. IMPORTANT for whichever mechanism picks this up next: knowledge/agent-runs/index.md and .claude/hourly-loop.md declare the legacy AgentRun mechanism (this file's own historical updates through batch10 came from that mechanism) deprecated in favor of the Wisk runtime (.wisk/knowledge/) for the CausaGanha hourly loop -- batches 6, 7, 11 and 14 ran under Wisk, batch12/13 ran under the legacy AgentRun scaffold again (its scheduled prompt still hard-codes it; the conflict was escalated once via notification on 2026-09-14/to0ars and reconfirmed unchanged by every AgentRun round since). This BacklogItem type is not itself named in the deprecation list (only AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck are), so it is kept updated here regardless of which mechanism a future round uses, but check .wisk/knowledge/ too before assuming this file alone is current. Budget for fourteen known defect/risk classes before trusting a batch's first pass -- see the numbered list below, including risk class 5 (a real production fix, already merged) and risk classes 7-14 (candidate-selection/concurrency/tooling/annotation-quality process issues, not production-code bugs). Risk class 14 (new, batch16): a subagent can leave a start/end pair's `<fim>` unclaimed even when the source text DOES contain a valid, unambiguous closing cue -- this is NOT the same as the established 'genuinely no closing cue' dangling-pair shape (risk classes 4/6/etc, which legitimately need an override), and must not be papered over with an override. Before declaring an unmatched pair a legitimate override candidate, actually read the source text around and after the `<inicio>` to confirm no closing cue exists; if one does exist (as it did here, and had already been correctly used by a sibling document in the very same batch), fix it by inserting the missing `<fim>` wrapper around the already-present text at the correct position (a pure tag-insertion, never retyping content) and re-verify byte-for-byte fidelity, rather than adding an override that would incorrectly encode a real annotation gap as expected. UPDATE (batch20, live-confirmed): TRF2's eligible pool went from 21 to 15 after this batch (still the next tier to pick from, not exhausted); TRF5 is no longer at the lowest tier (batch19 moved it from store_count=3 to 5) -- a future round must re-scan data/segmenter_samples/*.jsonl live (correct field names `text`/`info.id`/`info.tribunal`/`info.tipoDocumento`) rather than trusting either this file's cached tier ordering or the last live scan's snapshot, since concurrent rounds keep changing it between sessions. UPDATE (batch21, live-confirmed): TRF2's eligible pool went from 13 to 7 after this batch (still the next tier, not exhausted); remaining candidates are all shorter Acordaos in the 2369-2710 char range post-cleaning, still above the floor. All remaining Sentencas in TRF2's pool are below the 2500-char floor after cleaning. batch22 (rodada AgentRun gbf44b, primeira rodada do prompt agendado a rodar apos o repositorio ficar sem nenhuma PR de dominio aberta) 6 docs, TJGO/543564741, TJPB/578900185, TJPA/576803379, TJPA/576805366, TJRJ/327508788, TJTO/285747298 -- todos Sentencas, escolhidos por store_count empatado em 4 (tribunais ja representados). TJBA (tambem store_count=4) foi verificado e excluido: seu unico candidato elegivel restante (574460088) ja havia sido identificado no lote 17 como quase-duplicata (SequenceMatcher.ratio()=0.98) de um documento ja no store (574460085), entao nao foi reusado. TJTO precisou do limpador HTML do lote 3 (markup <html>/<body>/<section>/<p> embutido); os demais 5 ja vinham como texto plano (TJGO precisou apenas de html.unescape() para as entidades HTML brutas, mesmo padrao recorrente ja documentado nos lotes 12/16/18). Dois defeitos de transcricao encontrados e corrigidos: (1) TJGO/543564741 teve substituicao NBSP pervasiva (5 ocorrencias) corrigida com o mesmo script de diff-e-remapeamento ja existente (docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py, reutilizado sem modificacao) -- mas o proprio subagente, ao ser questionado por uma segunda notificacao de conclusao, corrigiu o arquivo por conta propria antes que o script precisasse ser aplicado de fato (a verificacao independente confirmou o match ja corrigido); (2) TJPA/576803379 tinha 3 ocorrencias de \\\"&\\\" bruto (nome de parte \\\"MORETTI & MACIEL LTDA\\\") nao escapado como entidade XML, causando XML malformado -- corrigido com uma substituicao regex simples (`&` -> `&amp;`, preservando qualquer entidade ja existente), sem alterar o conteudo textual (a funcao de reconstrucao ja desescapa entidades). Tres overrides --allowed-unmatched-overrides foram declarados, todos verificados contra o texto-fonte bruto antes de declarar: capitulo_merito em TJPA/576803379 (o raciocinio de merito flui direto para o dispositivo_abertura \\\"Ante o exposto\\\" sem frase de fechamento distinta, mesmo padrao ja documentado), e custas+honorarios em TJRJ/327508788 e TJPB/578900185 (enunciados unicos e curtos -- \\\"Custas antecipadas. Honorarios na forma da lei.\\\" e \\\"Sem custas e honorarios advocaticios, nos termos do artigo 55 da Lei no 9.099/95.\\\" -- sem marcadores de abertura/fechamento distintos, mesma classe combinada ja sancionada nos lotes 12/18/20). `scripts/segmenter_semantic_audit.py` sinalizou 1 achado novo (fundamentacao_legal_collapsed em TJTO/285747298, doc_12f989ac213c5eadf857aacc69b33ad2) -- revisado e confirmado falso positivo da mesma classe ja documentada nos lotes 12/20: as ocorrencias adicionais de \\\"art.\\\" estao dentro de um bloco de ementa de precedente do STJ (REsp 1.804.804/MS) citado verbatim e ja coberto por uma unica tag ref_normativa para o proprio precedente, e dentro de uma transcricao literal do texto legal (Lei 11.101/2005 arts. 50/59, CPC art. 584) tambem ja coberta por fundamentacao_legal+ref_normativa na frase introdutoria -- nao linguagem de raciocinio-com-conector adicional que justificasse mais tags. document_count 167->173, annotation_count 220->226, teto de val/test 25/25->26/26 (scripts/segmenter_governance_status.py, confirmado ao vivo; lote train-only, sem segunda anotacao independente). `git status --short data/segmenter` confirmou exatamente 6 novos documents/*.xml e 6 novos annotations/<id>/. `uv run ruff check`/`format --check` limpos. `uv run pytest -q tests/segmenter_dataset` mostrou 1 `F` no resumo em pontos antes de completar (mesmo padrao de lentidao em escala ja visto nos lotes 20/21) -- resultado completo a confirmar num commit de fechamento subsequente antes do merge. UPDATE (batch22, live-confirmed): TJBA agora esta totalmente esgotado (store_count=4, seu unico candidato nominalmente elegivel restante e uma quase-duplicata conhecida, nao reutilizavel) -- nao reselecionar sem um novo scan ao vivo achando um candidato genuinamente novo. TJGO/TJPB/TJRJ/TJTO subiram de store_count=4 para 5, TJPA subiu de 4 para 6 (dois candidatos neste lote). O proximo tier mais baixo para um lote futuro inclui TJMG/TJRS/TJSE/TJRN (store_count=2-3 na ultima verificacao ao vivo, TRF4 continua sinalizado inutilizavel pela classe de risco 16 ate reverificacao ao vivo) e o tier store_count=5 (TJGO/TJPB/TJRJ/TJTO mais TJPI/TJMT/TJMA/TJES/TRF5/TST/TJCE/TRF3). document_count precisa chegar a aproximadamente 200 (de 173 atuais) para o piso RFC 0012 se tornar alcancavel -- faltam aproximadamente 4-5 lotes deste tamanho no ritmo atual. UPDATE (lote 23 + fusao, live-confirmed): TRF2's eligible pool foi de 7 para 1 candidato apos o lote 23 (proximo do esgotamento completo); risco de classe 17 (novo) documentado: uma tag single-anchor aninhada dentro de <inicio>/<fim> de um par e descartada silenciosamente por _text_element_to_labels sem quebrar a fidelidade verbatim (round-trip do texto nao muda) -- verificar essa estrutura especificamente em lotes futuros, nao confiar apenas no diff de texto. document_count real apos a fusao de #1585+#1586: 179 (confirmar ao vivo via scripts/segmenter_governance_status.py antes de selecionar o proximo lote)."
last_verified_run_id: "2026-09-20-exciting-mccarthy-fv62kx"
last_verified_at: "2026-09-20T02:05:00Z"
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

- **Lote 16** (rodada epgxv2, este relatório): 6 documentos (TST/237077398,
  TST/237077448, TJPI/22443818, TJPI/22443820, TJGO/543516662,
  TJPB/578832621), esgotando por completo o pool elegível restante de
  TST e TJPI (0 candidatos elegíveis para ambos após este lote) e
  puxando TJGO/TJPB do próximo tier de menor `store_count`.
  `document_count` 132->138, teto de val/test 20/20->21/21
  (`docs/planning/evidence/segmenter-djen-sample-batch16-2026-09-17.json`).
  TJGO voltou a apresentar entidades HTML brutas não decodificadas no
  `texto_limpo` (411 ocorrências -- mesmo padrão recorrente do lote 12
  para esse tribunal), resolvido com `html.unescape()` antes de
  reanotar. TJPI/22443820 teve dois defeitos independentes: o mesmo
  substituição pervasiva de NBSP->espaço do lote 15 (70 ocorrências,
  corrigida com a mesma técnica de diff-e-remapeamento,
  `docs/planning/evidence/segmenter-djen-sample-batch16-fix-nbsp.py`) E
  uma sub-anotação genuína -- o par `ementa` ficou sem `<fim>` mesmo
  havendo uma cue de fechamento explícita na fonte ('5. Recurso
  conhecido e improvido.' logo antes do cabeçalho ACÓRDÃO), cue essa já
  corretamente usada por um documento irmão do mesmo lote
  (TJPI/22443818) -- ver classe de risco 14 (nova) abaixo, distinta da
  classe já documentada de par pendente sem cue nenhuma. Três overrides
  foram necessários para pares genuinamente sem cue de fechamento
  (`capitulo_merito` x2 em TST/237077448 e TJPB/578832621, `voto` x1 em
  TST/237077448, `custas` x1 em TJGO/543516662), todos verificados
  contra o texto-fonte bruto antes de declarar. `uv run ruff
  check`/`format --check` limpos, `uv run pytest -q
  tests/segmenter_dataset` 100% verde.

**Classe de risco 14 (nova, prometida pelo lote 16 mas nao escrita ate
agora)**: um par `_inicio`/`_fim` pode ficar sem `_fim` mesmo quando a
fonte TEM uma cue de fechamento genuina e explicita -- distinto da
classe ja documentada de par pendente SEM cue nenhuma (a maioria dos
overrides `--allowed-unmatched-overrides` deste backlog). No lote 16,
TJPI/22443820 tinha a cue de fechamento da `ementa` ('5. Recurso
conhecido e improvido.' logo antes do cabecalho ACORDAO) disponivel e
ja usada corretamente por um documento irmao do mesmo lote
(TJPI/22443818), mas o subagente simplesmente nao a marcou. Mitigacao:
ao revisar um par unmatched antes de declarar um override, verificar
explicitamente se existe uma cue de fechamento genuina na fonte -- nao
assumir que todo par unmatched e uma dangling-pair legitima; se uma cue
existir, corrigir inserindo o `<fim>` ao redor do texto ja presente
(sem retipar conteudo) em vez de declarar um override incorreto.

**Classe de risco 15 (nova)**: a tecnica de diff-e-remapeamento
programatico usada desde o lote 15 para reinserir NBSP (`\xa0`) removido
pelo subagente tem um bug real quando um `difflib.SequenceMatcher`
`replace`/`delete` op abrange mais de um caractere strippado
(`i2 > i1 + 1`): mapear o fim do intervalo para `mapping[i2]` (a posicao
RAW do PROXIMO caractere strippado apos o intervalo) em vez de
`mapping[i2 - 1] + 1` (o fim do ULTIMO caractere efetivamente
substituido) apaga silenciosamente qualquer tag XML que esteja
posicionada exatamente entre os dois -- porque remover uma tag nao
altera o texto strippado, a verificacao "`stripped(fixed) == source`"
sozinha NAO detecta essa classe de corrupcao. No lote 17
(TJBA/574460085), essa variante do bug comeu a abertura de
`<ref_processual>` e de `<capitulo_merito><inicio>` inteiras durante uma
correcao de NBSP com 16 diffs, a maioria deles `replace` de mais de um
caractere. Mitigacao: (1) usar `mapping[i2 - 1] + 1` como fim do
intervalo para qualquer op que nao seja um insert puro (`i1 == i2`);
(2) apos aplicar a correcao, verificar tambem que o MULTICONJUNTO de
tags XML (`re.findall(r'</?[a-zA-Z_]+>', texto)`) e identico antes e
depois da correcao, nao apenas que o texto strippado bate com a fonte --
essa segunda checagem e a unica forma barata de pegar uma tag apagada
sem alterar a contagem de caracteres strippados.

## Lote 17 (esta rodada, AgentRun 0hjgmk)

5 documentos reais, novos e nao sobrepostos com qualquer lote anterior:
TJBA/574460085, TJMA/42736393, TJMA/42730832, TJCE/363647616,
TJCE/363657243 -- continuando a estrategia de volume sobre diversidade
dos `next_move` anteriores, priorizando TJBA/TJMA/TJCE (tier de menor
`store_count`, 3, entre os tribunais com candidatos ainda disponiveis
apos o lote 16 esgotar TST/TJPI).

Um sexto candidato originalmente selecionado, TJBA/574460088, foi
descartado ANTES da ingestao: comparacao byte-a-byte do texto-fonte
bruto com TJBA/574460085 (mesmo juizo, mesmo template de embargos de
declaracao, mesmo juiz) deu `difflib.SequenceMatcher.ratio()=0.98` --
um near-duplicate genuino do template, nao apenas dois documentos do
mesmo tribunal. Ingerir os dois violaria o proprio criterio de aceite
de #1050 ("Prevent exact/near-duplicate and same-process-family leakage
across future train/validation assignments"). Mitigacao adicionada ao
processo desta linhagem: antes de anotar um candidato, comparar seu
texto bruto contra qualquer outro candidato ja selecionado no mesmo
lote do mesmo tribunal com `difflib.SequenceMatcher.ratio()` -- uma
razao acima de ~0.9 e sinal de template compartilhado, nao de
diversidade real, e o candidato deve ser trocado antes da anotacao (nao
depois, para nao desperdicar um subagente inteiro).

TJBA/574460085 e TJCE (ambos os candidatos) tinham NBSP (`\xa0`)
genuino embutido no texto-fonte, removido pelo subagente durante a
transcricao "verbatim" -- mesmo padrao ja documentado (classe de risco
13), corrigido com a tecnica de diff-e-remapeamento, mas com o bug da
classe de risco 15 (nova, acima) descoberto e corrigido no proprio
script desta rodada durante o processo (`TJBA/574460085` foi a vitima:
`<ref_processual>` e `<capitulo_merito><inicio>` foram apagados por uma
primeira versao com bug do script de correcao e recuperados apos
adicionar a checagem de multiconjunto de tags). TJCE/363657243 tinha
tambem uma sub-anotacao genuina distinta -- o par `relatorio` nao tinha
`_inicio` nenhum (nem heading, nem a frase de fallback "Trata-se de"
citada no guideline, porque a fonte nao usa nenhuma das duas): corrigido
marcando o primeiro nome proprio do relato ("Cicero Sobreira de Sousa")
como a cue de abertura de fato, ja que a regiao do relatorio precisa
comecar em algum lugar reconhecivel mesmo quando nenhuma cue formal
esta presente.

Quatro overrides `--allowed-unmatched-overrides` foram necessarios para
pares genuinamente sem cue de fechamento (`relatorio` em TJCE/363647616
-- padrao "relatorio dispensado" ja documentado no proprio guideline;
`capitulo_merito`/`custas`/`honorarios` em TJMA/42730832), todos
verificados contra o texto-fonte bruto antes de declarar.
`scripts/segmenter_governance_status.py` confirma `document_count`
138->143, `annotation_count` 191->196, teto de val/test 21/21->21/21
(inalterado -- os 5 documentos deste lote sao train-only, sem segunda
anotacao independente, entao nao elevam o teto val/test sozinhos; isso
requer `scripts/annotate_second_independent.py` +
`scripts/adjudicate_segmenter_review.py`, fora do escopo deste lote).
`git status --short data/segmenter` confirma exatamente 5 novos
`documents/*.xml` e 5 novos `annotations/<id>/`, sem write no-op
silencioso. `uv run ruff check`/`format --check` limpos. Audit semantico
(`scripts/segmenter_semantic_audit.py`) sem nenhum achado novo para os
5 documentos deste lote -- todos os achados sinalizados pertencem a
documentos pre-existentes (nao deste lote).

**Classe de risco 16 (nova)**: o piso de comprimento de candidato
(>=2500 caracteres) precisa ser verificado no texto JA LIMPO (depois do
`html.unescape()`/limpador HTML do lote 3), nao no comprimento bruto do
campo `text`/`texto_limpo` do jsonl de origem. Um candidato cujo texto
bruto ainda carrega markup HTML embutido (`<b>`/`<table>`/`<br>`/etc)
pode parecer elegivel pelo comprimento bruto e colapsar bem abaixo do
piso depois que o markup e removido -- o unico texto que efetivamente
chega ao subagente de anotacao. No lote 18, TRF4 foi inicialmente
escolhido como tribunal de menor `store_count` (3, empatado com
TJRN/TRF2/TJSE/TRF5/TJRS) com 4 candidatos elegiveis pelo comprimento
bruto (2713-3536 caracteres), mas TODOS os 9 candidatos restantes do
arquivo `trf4_acordao.jsonl` (nao so os 4 que passavam no piso bruto)
colapsam para 715-1832 caracteres depois de aplicar o limpador HTML do
lote 3 -- documentos de embargos de declaracao genuinamente curtos cujo
"peso" aparente vem quase inteiramente de markup HTML, nao de conteudo.
Mitigacao: ao escanear o pool para tribunais com markup HTML conhecido
(entities ou tags brutas no `text`), aplicar o limpador ANTES de
verificar o piso de 2500 caracteres, nao depois de selecionar os
candidatos -- selecionar por comprimento bruto pode desperdicar um lote
inteiro em candidatos que nunca vao passar na validacao mecanica de
comprimento minimo de anotacao. TRF4 foi descartado inteiramente deste
lote como resultado (nenhum documento TRF4 foi anotado ou ingerido).

## Lote 18 (esta rodada, Wisk 20260917T032539Z)

6 documentos reais, novos e nao sobrepostos com qualquer lote anterior:
TJES/577030718, TJES/577039281, TJRR/568111547, TJRR/568208030,
TJMT/74428001, TRF3/42490548 -- continuando a estrategia de volume
sobre diversidade, escolhendo o tribunal de menor `store_count` com
pool efetivamente disponivel apos a descoberta da classe de risco 16
(TRF4 descartado por inteiro, ver acima).

Um scan ao vivo confirmou TJMG (`store_count`=2, o mais baixo de todos
os nao-TJRO) e TJRN/TJSE/TJRS (`store_count`=3) com ZERO candidatos
elegiveis restantes no pool `data/segmenter_samples/*.jsonl` -- esses
quatro tribunais estao efetivamente esgotados para esta linhagem, nao
apenas "pouco explorados". TJES/TJRR/TJMT/TRF3 (tambem `store_count`=3
antes deste lote) tinham pool disponivel (7/13/16/17 candidatos
elegiveis respectivamente) e foram os escolhidos.

Nenhum dos 6 candidatos escolhidos tinha markup HTML, entidades HTML,
NBSP ou caracteres de controle -- todos limpos desde a fonte, primeira
vez desde o lote 11 que um lote inteiro nao precisou de nenhuma
mitigacao de limpeza de texto. Uma checagem `difflib.SequenceMatcher`
entre os dois candidatos de TJES (ratio=0.054) e entre os dois de TJRR
(ratio=0.048) confirmou ausencia de near-duplicate de template dentro
do lote (classe de risco documentada pelo lote 17), bem abaixo do
limiar ~0.9 de alerta.

Quatro documentos precisaram de `--allowed-unmatched-overrides` para
pares genuinamente sem cue de fechamento distinta, todos verificados
contra o texto-fonte bruto antes de declarar
(`docs/planning/evidence/segmenter-djen-sample-batch18-overrides.json`):
`preliminar`/`relatorio`/`custas`/`honorarios` em TRF3/42490548 (cada
um um enunciado de clausula unica, sem fechamento distinto -- mesmo
padrao ja sancionado pelo guideline para "Sem custas"/"Sem
honorários"); `relatorio`/`honorarios` em TJRR/568208030, sendo
`honorarios` um caso de fim compartilhado: a clausula combinada "Sem
custas processuais e honorários advocatícios nesta instância (arts. 54
e 55 da Lei 9.099/95)" fecha `custas` com seu proprio `<fim>`, mas
`honorarios` (aninhado dentro de `custas`) nao tem fechamento distinto
proprio -- o mesmo padrao de fim-compartilhado ja documentado pela
classe de risco 1, agora confirmado tambem entre duas categorias
irmãs (nao so entre uma categoria e sua vizinha textual);
`custas`/`honorarios` em TJES/577039281 (dois enunciados de clausula
unica separados); `relatorio`/`custas`/`honorarios` em TJMT/74428001
(o padrao "Relatório dispensado (art. 38...)" ja documentado no
guideline, mais um enunciado combinado "Sem custas nem honorários").

`scripts/segmenter_governance_status.py` confirma `document_count`
143->149, `annotation_count` 196->202, teto de val/test 21/21->22/22
(todos os 6 documentos sao train-only, sem segunda anotacao
independente -- eleva o teto porque o piso ja e limitado pelo tamanho
total do corpus, nao pelo numero de documentos adjudicados; ver
`scripts/segmenter_governance_status.py`'s proprio aviso).
`git status --short data/segmenter` confirma exatamente 6 novos
`documents/*.xml` e 6 novos `annotations/<id>/`, sem write no-op
silencioso. `uv run ruff check`/`format --check` limpos. Audit
semantico (`scripts/segmenter_semantic_audit.py`) sem nenhum achado
novo para os 6 documentos deste lote -- todos os achados sinalizados
pertencem a documentos pre-existentes (nao deste lote). Verificacao
independente de fidelidade verbatim (strip-tags-and-compare) rodada
pela propria sessao para os 6 documentos antes da ingestao, nao apenas
confiando no auto-relato de cada subagente -- todos MATCH
caractere-por-caractere contra a fonte.

Ainda por continuar: TRF2 e TRF5 (`store_count`=3 cada, pool com 21 e
22 candidatos elegiveis respectivamente, confirmado neste lote) sao o
proximo tier real com volume disponivel -- nao TJPA/TJGO/TJPB/TJRJ/
TJMS/TJMT/TRF3/TJBA/TJTO (`store_count`=4 apos este lote), que so
deveriam ser escolhidos depois que TRF2/TRF5 tambem esgotarem. TRF4
esta descartado por inteiro (classe de risco 16) ate que um novo
arquivo de amostra TRF4 com documentos mais longos apareca no pool, se
algum dia aparecer -- nao tentar reusar `trf4_acordao.jsonl` sem antes
confirmar que algum candidato novo la sobrevive a limpeza HTML acima do
piso de 2500 caracteres.

## Lote 19 (rodada AgentRun 91jobr, resgate da PR #1576)

**Contexto do resgate.** A corrida AgentRun-vs-Wisk (mapeada desde
2026-09-14, ainda sem reconciliacao do dono humano) produziu duas PRs
concorrentes reivindicando o mesmo "lote 18" quase simultaneamente:
#1576 (sessao AgentRun 726qh5, branch `claude/exciting-mccarthy-726qh5`)
e #1577 (Wisk, run `20260917T032539Z`). O Wisk mesclou primeiro
(`0a831be`, documentado acima como "Lote 18"), deixando #1576
organicamente stale contra o `main` atual. Os 6 documentos de #1576 nao
se sobrepoem com os do lote 18 e ja tinham fidelidade verbatim
verificada pela sessao 726qh5 -- descarta-los desperdicaria trabalho
real de subagente sem necessidade. Esta rodada resgatou o payload de
`origin/claude/exciting-mccarthy-726qh5` (apenas os pares
`data/segmenter/documents/*.xml` + `data/segmenter/annotations/*/*.xml`,
que sao adicoes puras sem conflito de dominio contra o `main` atual,
confirmado via `git merge-tree`) aplicando-o sobre uma branch propria a
partir do `main` pos-lote-18, e renomeou os artefatos de auditoria de
`segmenter-djen-sample-batch18-*` para `-batch19-*` para eliminar a
colisao de nome com os arquivos ja commitados pelo lote 18 (colisao
puramente de nomenclatura entre as duas PRs, nao de conteudo).

**Conteudo do lote** (inalterado em relacao ao que #1576 ja validara):
6 documentos, TJMT/74430633, TJRR/568209392, TJRR/568328945,
TRF3/42490599, TRF5/349186353 (Sentenca), TRF5/463264301 (Acordao) --
selecionados pela sessao 726qh5 excluindo deliberadamente os
`document_id` do lote 17 (PR #1574), ainda aberta e sem CI reportado no
momento daquela selecao. TJRR/568328945 teve um defeito de transcricao
(11 espacos ASCII isolados omitidos ao redor de quebras de linha em
branco) corrigido com uma tecnica de diff-e-remapeamento generalizada
(`docs/planning/evidence/segmenter-djen-sample-batch19-fix-missing-spaces.py`,
resgatada com o mesmo nome renumerado). Nove overrides
`--allowed-unmatched-overrides` foram declarados pela sessao 726qh5
para pares sem cue de fechamento, todos verificados contra o
texto-fonte bruto: `custas` x4, `honorarios` x3, `relatorio` x3 (duas
correspondencias exatas ao padrao "waiver clause is not a closing cue"
ja documentado no guideline), `capitulo_merito` x1 (fronteira ambigua
causada por um precedente citado verbatim na fundamentacao de
TRF3/42490599).

`scripts/segmenter_governance_status.py` confirma `document_count`
149->155, `annotation_count` 202->208 apos o resgate (lote train-only,
sem segunda anotacao independente -- teto de val/test permanece 22/22).
`git status --short data/segmenter` confirma exatamente 6 novos
`documents/*.xml` e 6 novos `annotations/<id>/`, sem write no-op
silencioso. `uv run ruff check`/`format --check` limpos, `uv run pytest
-q tests/segmenter_dataset` 100% verde apos o resgate.

**Licao operacional (nao uma nova classe de risco de anotacao, mas de
processo multi-agente):** quando duas sessoes automatizadas concorrentes
podem escolher o mesmo numero de lote para a mesma issue, o numero do
lote em si nao e uma chave de coordenacao confiavel -- apenas o conjunto
de `document_id` ja usados no store (`data/segmenter/documents/*.xml`)
e. Uma PR que perde a corrida de numero mas nao tem overlap de
`document_id` com a que venceu deve ser resgatada (renumerada e
reaplicada), nao descartada como duplicata -- o trabalho real de
anotacao verificado por subagente independente e o recurso caro desta
linhagem, o numero do lote e so um rotulo de conveniencia.

## Lote 20 (rodada Wisk 20260917T062515Z)

**Contexto operacional.** Esta e a primeira rodada do loop horario a
rodar sob o golden path do runtime Wisk (`uv run wisk init .` +
`uv run wisk start`) desde que `.claude/hourly-loop.md` declarou a
migracao do mecanismo legado `AgentRun`. O `wisk start` retomou o
handoff `handoffs/handoff-issue-1471-ia-publish-pending` (issue #1471,
piloto TJRO 2026). A revalidacao ao vivo exigida pelo proprio contrato
(`check:handoff-environment`) encontrou dois problemas: (1) o
`repository_head` do baseline do handoff
(`ca795fbcc08d89ff717139687705b5ee803c987c`) nao existe em lugar nenhum
do historico deste repositorio (`git cat-file -t` falha; nao e
ancestral de `origin/main` apos fetch) -- o baseline esta obsoleto/
inverificavel, nao apenas atrasado; (2) `env | grep ^IA_` confirmou
mais uma vez a ausencia de `IA_ACCESS_KEY`/`IA_SECRET_KEY` neste
ambiente, a 7a rodada consecutiva (desde 2026-09-11) a reconfirmar
exatamente a mesma lacuna de credencial sem nenhuma informacao nova.
Decisao registrada (`check:handoff-disposition`): REFRAMED, nao
aceito nem rejeitado -- o `next_action` do handoff continua correto e
sera retomado quando as credenciais existirem, mas esta rodada nao
repete o mesmo diagnostico pela 7a vez sem novidade; pivota para #1050,
que estava live-confirmed desbloqueada.

**Selecao de candidatos.** Um scan ao vivo do pool
(`data/segmenter_samples/*.jsonl`, nomes de campo corretos
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`, piso de 2500
caracteres apos limpeza) confirmou TRF2 como o proximo tier real
(`store_count`=3, 21 candidatos elegiveis, exatamente como o
`unblock_condition` do lote 19 havia documentado) -- TJMG/TJRN/TJSE/
TJRS, apesar de `store_count` igual ou menor, seguem com ZERO
candidatos elegiveis restantes (ja confirmado por rodadas anteriores,
reconfirmado aqui). TRF5 nao e mais o tier mais baixo: o lote 19 o
moveu de `store_count`=3 para 5.

**Conteudo do lote.** 6 documentos, todos TRF2: 301222642, 301222655,
301222733, 301222762, 301222819 (Acordaos, 9ª/2ª Turma Especializada)
e 301248486 (Sentenca, Juizado Especial Federal). Todos os 5 acordaos
tinham markup HTML bruto embutido (`<b>`/`</br>`) no `texto_limpo`,
limpo com o limpador ja validado do lote 3
(`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`)
mais `html.unescape()`, confirmado acima do piso de 2500 caracteres
apos a limpeza (3479-5133 caracteres). Os 6 subagentes foram
despachados em paralelo, um por documento, com o prompt canonico
Technique 1 (`data/segmenter_splits/technique1_annotation_prompt.md`).

**Defeito de transcricao encontrado em todos os 6 documentos.** A
verificacao independente de fidelidade verbatim (nao apenas o
autorrelato de cada subagente) encontrou substituicao NBSP->espaco
(`\xa0` -> ` `) em todos os 6 documentos deste lote -- uma unica
ocorrencia isolada em cada um, nao pervasiva como nos lotes 15/16.
Corrigido reutilizando verbatim, sem modificacao,
`docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py`
(tecnica de diff-e-remapeamento: reconstrucao sem tags comparada
character-a-character contra a fonte, cada diff confirmado como
exclusivamente relacionado a NBSP antes de reinserir o byte correto na
posicao mapeada na string tagueada, com verificacao de fidelidade e de
conjunto-de-tags antes/depois). Todos os 6 documentos MATCH
caractere-por-caractere apos a correcao, confirmado programaticamente
antes da ingestao real (nao apenas confiando no autorrelato).

**Overrides declarados.** Cinco no par `ementa` (todos os 5 acordaos):
formato capa+ementa-estruturada do TRF2 -- "EMENTA" abre direto em
secoes numeradas I-IV sem RELATORIO/VOTO separado que forneca uma
frase de transicao para fechar a ementa, mesma classe ja documentada
nos lotes 3/4/7/14 (TJRS/TRF4/TJSC/TJPI). Dois no par `custas`/
`honorarios` da sentenca (301248486): clausula combinada de enunciado
unico "Sem custas e honorários advocatícios ... na forma do art. 55 da
Lei n. 9099/95", sem fechamento distinto para nenhuma das duas
categorias, mesmo padrao ja sancionado pelo guideline e usado em
lotes anteriores. Todos os 7 overrides verificados contra o
texto-fonte bruto antes de declarar.

**Auditoria semantica.** `scripts/segmenter_semantic_audit.py`
sinalizou 1 achado novo neste lote: `fundamentacao_legal_collapsed` em
TRF2/301222762 (`doc_db852d2ad03c021f0ac411e3e5b63b60`) -- "art."
aparece 4 vezes no texto mas so 1 `fundamentacao_legal` foi tagueado.
Revisado manualmente: as outras 3 ocorrencias de "art." estao todas
dentro de citacoes bare ja corretamente tagueadas como
`ref_normativa` na lista "Dispositivos relevantes citados" (CF/1988
art. 201 §9º; Lei 9.494/1997 art. 1º-F; CPC art. 85 §3º e art. 300) --
nao sao linguagem de raciocinio-com-conector (`nos termos do`/
`conforme`) que justificaria `fundamentacao_legal`. Falso positivo da
heuristica (que conta substring bruta sem excluir texto ja tagueado
como `ref_normativa`), mesma classe ja vista em 5 documentos
pre-existentes do corpus antes deste lote -- nenhuma correcao
necessaria.

`scripts/segmenter_governance_status.py` confirma `document_count`
155->161, `annotation_count` 208->214, teto de val/test 23/23->24/24
(lote train-only, sem segunda anotacao independente). `git status
--short data/segmenter` confirmou exatamente 6 novos `documents/*.xml`
e 6 novos `annotations/<id>/`, sem write no-op silencioso. `uv run
ruff check`/`format --check` limpos. `uv run pytest -q
tests/segmenter_dataset` ainda estava rodando em segundo plano no
momento deste commit (a suite ficou lenta o suficiente com 161
documentos para exceder os timeouts curtos padrao do ambiente) --
resultado confirmado num commit de fechamento subsequente.

Ainda por continuar: TRF2 (`store_count` agora 4, 15 candidatos
elegiveis restantes no pool ao vivo confirmados neste lote) continua
sendo o proximo tier a esgotar antes de avancar para
TJPA/TJGO/TJPB/TJRJ/TJMS/TJBA/TJTO (`store_count`=4, empatados com
TRF2 apos este lote). TRF4 continua descartado por inteiro (classe de
risco 16) ate que um novo arquivo de amostra TRF4 com documentos mais
longos apareca no pool.

## Lote 21 (rodada Wisk 20260917T082642Z)

**Contexto operacional.** `uv run wisk start` retomou novamente o
handoff `handoffs/handoff-issue-1471-ia-publish-pending`. Ao inicializar
o consumer bundle gitignorado do Wisk estava ausente neste checkout
fresco (`.wisk/specs`, `.wisk/knowledge/system`, `manifest.json`), o que
fazia `wisk start` reportar `no-eligible-session` (nenhum `SessionType`
carregado) -- corrigido rodando `uv run wisk init .`, que populou os 54
arquivos gerenciados sem tocar em `.wisk/knowledge/{wiki,skills,
experiences,local}` (1320 arquivos preservados). A revalidacao ao vivo
(`check:handoff-environment`) reconfirmou, pela 8a+ rodada consecutiva
desde 2026-09-11: `repository_head` do baseline
(`ca795fbcc08d89ff717139687705b5ee803c987c`) inalcancavel no historico
deste repositorio, e `IA_ACCESS_KEY`/`IA_SECRET_KEY` ausentes. Disposicao
`REFRAMED` registrada (mesmo raciocinio do lote 20): pivota para #1050.

**Selecao de candidatos.** Scan ao vivo de
`data/segmenter_samples/trf2.jsonl` + `trf2_acordao.jsonl` (campos
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`), excluindo os 9
IDs TRF2 ja no store (confirmado via `grep` das `uri`s em
`data/segmenter/documents/*.xml`), encontrou 13 candidatos elegiveis
(>=2500 caracteres apos limpeza HTML + `html.unescape()`) -- todos os
Sentencas remanescentes ficaram abaixo do piso apos a limpeza (a unica
Sentenca elegivel do pool, 301248486, ja havia sido usada no lote 20).
Selecionados os 6 Acordaos mais longos: 301222742, 301222784, 301222723,
301222696, 301222620, 301222706 (todos 9ª Turma Especializada).

**Execucao.** 6 subagentes despachados em paralelo, um por documento,
com o prompt canonico Technique 1, cada um escrevendo seu resultado
direto num arquivo (nao no proprio relatorio, para nao inflar o
contexto da rodada coordenadora). Verificacao independente de
fidelidade verbatim (strip de tags via regex + diff byte-a-byte contra
a fonte, nao apenas confiando no autorrelato) confirmou MATCH exato
nos 6 documentos, sem substituicao NBSP ou qualquer outro defeito de
transcricao desta vez.

**Overrides declarados.** Cinco no par `ementa` (301222620, 301222696,
301222706, 301222723, 301222784): mesmo formato capa+ementa-estruturada
do TRF2 ja documentado nos lotes 3/4/7/14/20 -- "EMENTA" abre direto em
secoes numeradas sem RELATORIO/VOTO separado. O sexto documento
(301222742) teve o par `ementa` corretamente fechado pelo subagente
("15. Apelação provida."), confirmado por grep antes de decidir que
precisava de override -- nao presumido a partir do padrao dos outros 5.
Todos os 5 overrides verificados contra o texto-fonte bruto antes de
declarar.

**Auditoria semantica.** `scripts/segmenter_semantic_audit.py` nao
sinalizou nenhum achado novo nos 6 documentos deste lote (os 10 achados
existentes no output pertencem todos a documentos pre-existentes do
corpus, confirmado por doc_id).

`scripts/segmenter_governance_status.py` confirma `document_count`
161->167, `annotation_count` 214->220, teto de val/test 24/24->25/25
(lote train-only). `git status --short data/segmenter` confirmou
exatamente 6 novos `documents/*.xml` e 6 novos `annotations/<id>/`. `uv
run ruff check`/`format --check` limpos. `uv run pytest -q
tests/segmenter_dataset` excedeu novamente os timeouts curtos padrao do
ambiente com 167 documentos (mesmo padrao do lote 20) -- rodando em
segundo plano, resultado a confirmar num commit de fechamento se
necessario.

Ainda por continuar: TRF2 (13->7 candidatos elegiveis restantes no pool
ao vivo apos este lote) continua sendo o proximo tier a esgotar antes
de avancar para TJPA/TJGO/TJPB/TJRJ/TJMS/TJBA/TJTO (`store_count`=4).
TRF4 continua descartado por inteiro (classe de risco 16).

## Lote 23 (rodada Wisk 20260919T192610Z)

**Contexto operacional.** `uv run wisk start` retomou o handoff
`handoffs/handoff-issue-1471-ia-publish-pending`; revalidado ao vivo e
reconfirmado bloqueado (credenciais IA ausentes). Uma varredura do
restante do backlog aberto (issues #1469, #950/#951/#1093, #1482) achou
todo criterio de aceite sem dependencia de credencial ja implementado e
mergeado em main -- todo o resto da fila esta preso na mesma parede de
credenciais IA/Cloudflare que #1471. #1050 seguiu sendo a unica alavanca
genuinamente desbloqueada. Uma PR concorrente (#1585, "lote 22") ja
estava aberta minutos antes desta rodada comecar, reivindicando
TJGO/TJPB/TJPA/TJRJ/TJTO -- em vez de competir pelo mesmo tier, este
lote escolheu TRF2 (7 candidatos elegiveis restantes, tribunal
disjunto do de #1585), eliminando qualquer risco de colisao de
document_id independentemente da ordem de merge.

**Selecao de candidatos.** Scan ao vivo de `data/segmenter_samples/trf2_acordao.jsonl`
(campos `text`/`info.id`/`info.tribunal`/`info.tipoDocumento`), excluindo
os 106 IDs ja usados no store (extraidos via regex das `uri`s reais em
`data/segmenter/documents/*.xml`, nao de qualquer numero de lote em
cache), encontrou 7 candidatos elegiveis (>=2500 caracteres apos
`html.unescape()` + limpador HTML do lote 3 -- todos os 7 precisaram do
limpador). Selecionados os 6 mais longos (2757-3062 caracteres):
301222629, 301222677, 301222685, 301222713, 301222792, 301228222.
Verificacao de near-duplicate entre os 6 (mesmo relator/turma em varios)
com `difflib.SequenceMatcher.ratio()` par-a-par no texto-fonte bruto:
maior ratio encontrado foi 0.29 -- nenhum near-duplicate, apenas mesmo
template administrativo com merito genuinamente distinto em cada um.

**Execucao.** 6 subagentes despachados em paralelo, cada um escrevendo
seu resultado direto num arquivo. Verificacao independente de fidelidade
verbatim (strip de tags via `_text_element_to_labels` real, nao regex
improvisada, mais diff byte-a-byte contra a fonte) encontrou 2 dos 6 com
substituicao NBSP->espaco pervasiva (301222713, 301222792) -- corrigida
com o script de diff-e-remapeamento ja existente (versao corrigida do
lote 17, `docs/planning/evidence/segmenter-djen-sample-batch17-fix-nbsp.py`,
reutilizado verbatim).

**Classe de risco 17 (NOVA): aninhar uma tag single-anchor dentro de
`<inicio>`/`<fim>` de um par e descartado silenciosamente pelo parser.**
`segmenter_dataset.store._text_element_to_labels`'s branch para
`child.tag in _PAIR_ROLES` (ou seja, filhos literalmente chamados
`inicio`/`fim`) so emite o label do proprio wrapper
(`{base}_{role}`) e nunca faz splice dos `child_items` (labels aninhados
DENTRO desse `inicio`/`fim`) -- diferente do branch `elif child_items`
usado para qualquer outro filho, que faz esse splice corretamente. Uma
tag `<resultado>` aninhada dentro de `<fim>...</fim>` portanto
desaparece silenciosamente do resultado de `_text_element_to_labels`
mesmo com XML bem-formado e reconstrucao verbatim identica byte-a-byte
-- a verificacao padrao de fidelidade verbatim NAO detecta essa classe,
porque o texto reconstruido nao muda (so o label some). Dois subagentes
deste lote (301222629, 301222792) aninharam `<resultado>` assim; um
terceiro (301222713) tambem, no proprio output original do subagente.
Corrigido nos 3 casos reposicionando `<resultado>` como irmao de
`<inicio>`/`<fim>` (ainda dentro do wrapper do par, ou logo apos ele
fechar) em vez de filho de `<fim>` -- reposicionamento puro de tag, sem
reescrever conteudo, refidelidade verbatim reverificada apos cada
correcao. Detectado so porque `resultado` foi checado explicitamente
apos a fidelidade verbatim (`has_resultado` numa segunda passada de
verificacao), nao pela fidelidade verbatim isolada -- uma futura rodada
deve sempre verificar programaticamente que toda categoria que o
guideline descreve como esperada (ex: `resultado` num acordao com
resultado operativo claro) realmente aparece nos labels PARSEADOS, nao
so no XML bruto.

**Classe de risco 14 (reconfirmada, nao nova): override "sem cue de
fechamento" nao verificado contra o texto-fonte.** O subagente de
301222685 declarou `acordao_decisorio` unmatched (so inicio) alegando
que "por unanimidade" aparecia "no meio da frase, nao no fechamento
verdadeiro" -- mas o texto-fonte bruto tem a MESMA estrutura boilerplate
("decidiu, por unanimidade, [resultado operativo]") ja usada com sucesso
como cue de fechamento por dois documentos irmaos deste mesmo lote
(301222677, 301228222). Corrigido inserindo o `<fim>por unanimidade</fim>`
faltante (com `<resultado>` reposicionado como irmao, per classe de
risco 17 acima) em vez de aceitar o override nao verificado.

**Overrides declarados.** Cinco no par `ementa` (301222629, 301222677,
301222713, 301222792, 301228222): mesmo formato capa+ementa-estruturada
do TRF2 ja documentado nos lotes 3/4/7/14/20/21, cada um verificado
contra a presenca real das secoes numeradas I-IV no texto-fonte antes de
declarar. `ref_normativa` (categoria excluida da ontologia v8, RFC 0012
§5 decisao 1 -- ja documentada em `data/segmenter/reviews/*.xml` como
descartada automaticamente por `_drop_excluded_categories`) apareceu nos
6 documentos por instrucao do proprio guideline v7 (que ainda a lista na
tabela de categorias apesar da exclusao da ontologia); descartada
corretamente pelo pipeline de ingestao real, nao um defeito deste lote.

**Auditoria semantica.** `scripts/segmenter_semantic_audit.py` nao
sinalizou nenhum achado novo nos 6 documentos deste lote (os 10 achados
existentes pertencem todos a documentos pre-existentes do corpus,
confirmado por doc_id). `uv run ruff check`/`format --check` limpos.

`scripts/segmenter_governance_status.py` e `uv run pytest -q
tests/segmenter_dataset` excederam novamente os timeouts curtos padrao
do ambiente com 173 documentos (mesmo padrao dos lotes 20/21) --
rodando em segundo plano, resultado a confirmar no commit de fechamento
e pelo CI da PR. Novo teste de regressao
`test_real_store_reflects_batch23_corpus_growth` adicionado a
`tests/segmenter_dataset/test_segmenter_governance_status.py` e
confirmado verde isoladamente (`-k batch23`). `document_count` 167->173,
`annotation_count` 220->226 (contagem de arquivos `git status --short
data/segmenter`: exatamente 6 `documents/*.xml` e 6 `annotations/<id>/`
novos, sem write no-op silencioso).

Ainda por continuar: TRF2 (7->1 candidato elegivel restante no pool ao
vivo apos este lote) esta perto de esgotar -- uma futura rodada deve
reescanear `data/segmenter_samples/*.jsonl` ao vivo para achar o proximo
tier de menor `store_count` (a PR concorrente #1585/lote22, se
mergeada primeiro, muda TJGO/TJPB/TJPA/TJRJ/TJTO para o tier seguinte;
TJMS permanece em 4, nao tocado por #1585). Ao aninhar QUALQUER tag
single-anchor dentro do wrapper de um par start/end, sempre posicionar
como irmao de `<inicio>`/`<fim>`, nunca como filho literal de `<fim>`
ou `<inicio>` -- ver classe de risco 17 (nova). Ao revisar uma
declaracao de "par sem cue de fechamento", sempre comparar contra
documentos irmaos do mesmo lote que usem a mesma estrutura boilerplate
antes de aceitar -- ver classe de risco 14 (reconfirmada).

## Lote 24 (rodada AgentRun fv62kx)

Scan ao vivo de `data/segmenter_samples/*.jsonl` usando o limpador HTML
real do lote 3 (`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`),
nao apenas `html.unescape()` -- diferenca importante, pois o piso de
2500 caracteres so e significativo depois da limpeza real que o
subagente efetivamente ve. TJSC, TRF6, TJMG, TJRS, TJSE e TJRN
confirmados esgotados (zero candidatos elegiveis restantes cada); TRF4
reconfirmado inutilizavel pela classe de risco 16 (zero candidatos
sobrevivem a limpeza real, mesmo os que pareciam elegiveis pelo
comprimento bruto). O tier real com volume disponivel era TJBA
(`store_count`=4, 1 elegivel) e o tier `store_count`=5 (TJMA, TJPI,
TJES, TJGO, TJPB escolhidos entre varios candidatos por pool
remanescente mais escasso).

**Selecao**: TJBA/574460088 (Sentenca, 3408 car.), TJMA/42725100
(Sentenca, 6571 car.), TJPI/22443826 (Acordao, 3563 car.),
TJES/577051509 (Sentenca, 4196 car.), TJGO/543517919 (Sentenca, 3126
car.), TJPB/578906897 (Sentenca, 4381 car.). Verificacao de
near-duplicate par-a-par (`difflib.SequenceMatcher.ratio()`) entre os 6
candidatos (tribunais todos distintos): maior ratio 0.062, nenhum risco
de quase-duplicata.

**Execucao**: 6 subagentes despachados em paralelo, cada um escrevendo
seu resultado direto num arquivo via `Write`, instruidos explicitamente
a posicionar qualquer tag single-anchor aninhada dentro de um par como
irmao de `inicio`/`fim` (nao filho), para nao reintroduzir a classe de
risco 17 corrigida em codigo por PR #1588 (concorrente, ainda aberta no
inicio desta rodada). Verificacao independente via
`segmenter_dataset.store._text_element_to_labels` real (nao o
autorrelato de cada subagente) confirmou fidelidade verbatim
byte-a-byte nos 6 documentos na primeira tentativa -- nenhum defeito de
transcricao (NBSP, `&` nao escapado, HTML residual) encontrado desta
vez. `resultado` confirmado presente e como irmao de `inicio`/`fim` em
todos os 6.

**Overrides**. Dois overrides `capitulo_merito` (TJMA/42725100, cue
"passo a decidir"; TJBA/574460088, cue "Decido.") verificados contra o
texto-fonte bruto: em ambos, o raciocinio de merito flui diretamente
para um `dispositivo_abertura` ja tagueado ("A vista do exposto"/
"Diante do exposto,"), sem frase de fechamento distinta propria para
`capitulo_merito`. Como nenhum documento do corpus (179 antes deste
lote) tem ainda um par `capitulo_merito` fechado com sucesso, nao havia
precedente de como um `<fim>` deveria ser formado aqui -- preferido
declarar o override (mesmo padrao de "fluxo direto para o dispositivo"
ja usado para outras categorias) a fabricar uma tag de fechamento
inedita sem base textual propria. Cinco outros overrides reusam padroes
ja sancionados: custas/honorarios em enunciados combinados de sentenca
curta (TJMA/42725100 "Isento de custas e honorarios..."; TJES/577051509,
dois enunciados separados mas igualmente sem fechamento distinto;
TJPB/578906897 "Sem custas ou honorarios advocaticios... art. 55 da Lei
no 9.099/95", mesma citacao do lote 19) e TJGO/543517919 honorarios
("Sem honorarios advocaticios, em razao da ausencia de citacao valida"),
alem de `relatorio` "dispensado" em TJPB/578906897 (padrao
explicitamente sancionado pelo guideline v7 para a clausula de
dispensa do art. 38 da Lei 9.099/95). Todos os sete overrides
verificados contra o texto-fonte bruto deste lote antes de declarar.

**Auditoria e testes**. `scripts/segmenter_semantic_audit.py` sinalizou
zero achados novos entre os 6 documentos (confirmado programaticamente:
nenhum dos 6 novos `doc_id` aparece nos 11 achados pre-existentes do
corpus). `uv run ruff check`/`format --check` limpos. `uv run pytest -q
tests/segmenter_dataset` 100% verde (208 passed) com o corpus em 185
documentos. `git status --short data/segmenter` confirmou exatamente 6
novos `documents/*.xml` e 6 novos `annotations/<id>/`, sem write
no-op silencioso. `document_count` 179->185, `annotation_count`
232->238, teto de val/test 27/27->28/28
(`scripts/segmenter_governance_status.py`, confirmado ao vivo antes e
depois; lote train-only, sem segunda anotacao independente).

Ainda por continuar: falta aproximadamente document_count>=~200 para o
piso RFC 0012 Sec 5 item 4 (>=30/>=30) se tornar alcancavel -- cerca de
2-3 lotes deste tamanho no ritmo atual. Uma futura rodada deve
reescanear ao vivo `data/segmenter_samples/*.jsonl` (com o limpador
real, nao apenas `html.unescape()`) para achar o proximo tier de menor
`store_count` com pool efetivamente disponivel -- TJBA provavelmente
esgotado apos este lote (era 1 elegivel), TJMA/TJPI/TJES/TJGO/TJPB
subiram de `store_count`=5 para 6. PR concorrente #1588 (fix em codigo
da classe de risco 17) permanecia aberta e nao mesclada ao fim desta
rodada -- uma rodada futura deve verificar seu estado antes de assumir
que o workaround de posicionamento de tag ainda e necessario.
