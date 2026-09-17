---
type: AgentDecision
id: "2026-09-17-exciting-mccarthy-0hjgmk-decision-drop-near-duplicate-and-fix-diff-remap-bug"
run_id: "2026-09-17-exciting-mccarthy-0hjgmk"
goal_id: "2026-09-17-exciting-mccarthy-0hjgmk-goal-djen-sample-batch17"
question: "Dois problemas reais surgiram durante a anotacao do lote 17: (1) TJBA/574460088, um dos 6 candidatos originalmente selecionados, tem 98% de similaridade byte-a-byte com TJBA/574460085 (mesmo juizo/juiz/template de embargos de declaracao) -- inclui-lo violaria o proprio criterio de aceite de #1050 contra leakage de near-duplicates. (2) O script de correcao de NBSP por diff-e-remapeamento (reusado desde o lote 15) apagou silenciosamente as tags <ref_processual> e <capitulo_merito><inicio> de TJBA/574460085 durante uma correcao com multiplos diffs adjacentes -- a verificacao existente ('texto strippado bate com a fonte') nao detectou a corrupcao porque remover uma tag XML nao muda o texto strippado. Como proceder: (a) incluir TJBA/574460088 mesmo assim, (b) reduzir o lote para 5 documentos descartando-o, e (c) confiar no output do script de correcao sem verificacao adicional ou adicionar uma checagem separada de integridade de tags?"
choice: "(b) Descartar TJBA/574460088 do lote, reduzindo-o para 5 documentos -- qualidade e ausencia de leakage sobre rigidez de tamanho de lote. (c-adicional) Corrigir o bug do script de diff-e-remapeamento (usar o fim do ULTIMO caractere substituido, nao o inicio do PROXIMO, como fim do intervalo de substituicao) e adicionar uma segunda checagem pos-correcao: o multiconjunto de tags XML deve ser identico antes e depois da correcao, alem da checagem existente de texto strippado."
rationale: "Para (a): #1050 declara explicitamente como criterio de aceite 'Prevent exact/near-duplicate and same-process-family leakage across future train/validation assignments' -- incluir um documento com ratio=0.98 contra um sibling do mesmo lote seria quase certamente uma violacao desse criterio, mesmo que os dois tenham IDs de documento distintos (nomes/numero de processo diferentes o suficiente para nao colidir no dedup por (tribunal,id), mas nao o suficiente para constituir um segundo exemplo real independente do template). Cortar 1 de 6 candidatos e um custo trivial comparado ao risco de poluir o corpus de treino com um near-duplicate que uma rodada futura teria que descobrir e reverter (como ja aconteceu no lote 14, risco classe 12). Para (c): a verificacao original ('texto strippado bate com a fonte') e cega a corrupcao de tags por construcao -- uma tag removida nao aparece na diferenca de texto strippado, entao confiar apenas nela deixaria esse bug (e qualquer recorrencia futura da mesma classe) invisivel ate um erro de parsing XML mais tarde no pipeline de ingestao, ou pior, um XML mal-formado que passasse silenciosamente. Adicionar a checagem de multiconjunto de tags custa uma linha de codigo e fecha essa lacuna de verificacao permanentemente para qualquer uso futuro dessa tecnica (lotes 15+ ja a usam rotineiramente para o defeito de NBSP)."
---

# Decisao: descartar near-duplicate, corrigir e reforcar o script de correcao de NBSP

TJBA/574460088 foi descartado do lote (98% de similaridade com
TJBA/574460085) para nao introduzir leakage de near-duplicate no corpus.
O script de diff-e-remapeamento de NBSP (usado desde o lote 15) tinha um
bug real que apagava tags XML adjacentes a uma correcao de multiplos
caracteres sem que a verificacao existente detectasse -- corrigido
usando o fim do ultimo caractere substituido (nao o inicio do proximo)
como fronteira do intervalo, e reforcado com uma checagem adicional de
multiconjunto de tags antes/depois da correcao. Ambos os achados foram
registrados em `knowledge/backlog/issue-1050.md` como classes de risco
14 (finalizando um forward-reference que o lote 16 tinha deixado
incompleto) e 15 (nova).
