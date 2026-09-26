---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-p08457-decision-adjudication-resolutions"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
question: "As duas segundas anotacoes independentes (model_family=prompt_subagents:haiku) discordaram da primeira em alguns pontos e uma delas (TRF6) tinha um bug estrutural de aninhamento XML causando overlap mecanico. Como resolver cada divergencia na adjudicacao final, e e aceitavel corrigir o bug estrutural antes de adjudicar em vez de descartar a anotacao inteira?"
choice: "TRF6: corrigido o aninhamento estrutural (ref_processual estava aninhado dentro do wrapper <inicio> do cabecalho, causando overlap) movendo o fechamento de </inicio> para antes de '  Nº ' -- uma correcao estrutural sem julgamento de conteudo, ja que ambas as anotacoes concordavam que ref_processual e o mesmo span de texto. Apos a correcao, a resolucao final adota a leitura mais enxuta da anotacao A (ancoras mais curtas, conforme Regra 1) e rejeita a unica tag adicional de B (fundamentacao_legal sobre 'nos termos do voto do(a) Relator(a)', que nao cita autoridade especifica). TRF2: a resolucao combina as dus anotacoes -- adota cabecalho de B (omitido por A sem razao aparente), mantem todas as 4 ocorrencias de fundamentacao_legal de A (B omitiu uma, violando a regra 'tag every distinct occurrence'), e restaura o resultado ('NEGAR PROVIMENTO') que B omitiu inteiramente."
rationale: "Corrigir um bug estrutural de aninhamento XML (nao uma escolha de conteudo) antes de adjudicar preserva a independencia genuina da segunda anotacao -- a correcao nao usa nenhuma informacao da anotacao A, so aplica a propria regra da guideline (ancoras curtas, cabecalho_inicio nao deve englobar outro anchor). Isso e diferente das duas tentativas anteriores rejeitadas do handoff (doc_82d8ee7168b24d787ce0417f888d1eb3), que tinham erros de conteudo genuinos (clausula solta, normalizacao de aspas, tags de ancora unica duplicadas) nao corrigiveis sem reescrever substancia. Em ambos os documentos desta rodada, a alta concordancia inter-anotador (6 de 7 ancoras em TRF6; 9 de 11 em TRF2) e um sinal de qualidade real da segunda anotacao, nao um artefato de bug -- justificando adjudicar em vez de descartar e tentar de novo."
---

# Decisao: resolucoes de adjudicacao para TRF6 e TRF2

TRF6: corrigido um bug estrutural de aninhamento (nao de conteudo) na
segunda anotacao antes de adjudicar; resolucao final adota a leitura
mais enxuta de A, rejeitando a unica tag adicional de B por nao citar
autoridade especifica. TRF2: resolucao combina as duas anotacoes --
adota o cabecalho novo de B, mas restaura de A a ocorrencia de
fundamentacao_legal e o resultado que B omitiu.
