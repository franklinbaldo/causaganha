---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-f0q3d4-evidence-adjudication-decisions"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
goal_id: "2026-09-15-exciting-mccarthy-f0q3d4-goal-scale-segmenter-reviews"
kind: "review"
reference: "data/segmenter/reviews/doc_c502b14fd24cd8133897a1863d25e30a/rev_67960d131e9447ca14ade3647c3516a2.xml ; data/segmenter/reviews/doc_4d89a2699daf927cca28e543ebfd3efc/rev_f59fee4dd46b66b2f0f9126f8ddf395c.xml"
summary: "diff_labels sobre os 2 pares independentes mostrou desacordos reais e não-triviais: a anotação histórica llm_technique1:batch1 omitiu cabecalho inteiramente nos dois documentos (adicionado via a nova anotação), enquanto a nova anotação (subagente haiku) tagueou acordao_decisorio_inicio/resultado/ementa_fim/acordao_decisorio_fim mais longos que o padrão canônico da Regra 1 do guideline (âncoras curtas). Resolução adotou o span mais curto/canônico em cada caso de desacordo de fronteira, e a adição genuína (cabecalho) da nova anotação."
---

# Evidência: decisões de adjudicação registradas em cada ReviewRecord

Para `doc_c502b14fd24cd8133897a1863d25e30a` (8 labels matched, 2 só em A, 4
só em B): a anotação histórica A não tagueava `cabecalho` (adotado de B);
A usava `acordao_decisorio_inicio`="Vistos, relatados e discutidos" (30
caracteres, igual ao próprio exemplo do guideline) contra a versão de B que
se estendia por 200 caracteres até a vírgula antes do resultado — violação
clara da Regra 1 ("anchor spans are short... typically 1-5 words, never more
than ~120 characters"); adotado A. Mesmo padrão para `resultado`: A="NÃO
PROVIDOS" (verbo operativo puro) contra B="EMBARGOS DE DECLARAÇÃO NÃO
PROVIDOS" (inclui o sujeito) — adotado A, mais alinhado ao exemplo do
guideline ("julgo procedente" / "nego provimento").

Para `doc_4d89a2699daf927cca28e543ebfd3efc` (7 labels matched, 3 só em A, 5
só em B): mesmo padrão -- `cabecalho` ausente em A (adotado de B);
`ementa_fim`, `acordao_decisorio_inicio` e `acordao_decisorio_fim` de A
consistentemente mais curtos/canônicos, adotados sobre as versões mais
longas de B.

Em ambos os documentos, a nova anotação (subagente Técnica 1, modelo
`haiku`, família `prompt_subagents:haiku`) capturou uma categoria inteira
que a anotação histórica tinha perdido (`cabecalho`), mas também exibiu uma
tendência sistemática a âncoras longas demais em `acordao_decisorio_inicio`
— um padrão de erro registrado aqui para uma rodada futura considerar ao
reforçar o prompt de Técnica 1 (o prompt já avisa sobre âncoras curtas, mas
evidentemente não o suficiente para este caso específico de acórdão com
preâmbulo longo antes do resultado operativo).
