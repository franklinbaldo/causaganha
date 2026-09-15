---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-b3xdwp-decision-trim-numbered-heading-prefixes"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
question: "Em doc_6b714f6515beb1d38ba465e57c60c669, as duas anotações discordaram em relatorio_inicio: A marcou 'I - RELATÓRIO' (incluindo o numeral romano da seção), B marcou só 'RELATÓRIO'. A anotação histórica também usou o mesmo padrão de incluir o numeral em capitulo_merito_inicio ('II - FUNDAMENTAÇÃO') e capitulo_merito_fim ('III - DISPOSITIVO'), categoria que B não anotou (falso negativo total, não disagreement de fronteira). Deve o numeral romano de seção entrar na âncora?"
choice: "Não. Adotada a âncora sem o numeral romano nas três posições (relatorio_inicio='RELATÓRIO', capitulo_merito_inicio='FUNDAMENTAÇÃO', capitulo_merito_fim='DISPOSITIVO'), mesmo capitulo_merito não tendo disagreement direto (B simplesmente não anotou a categoria)."
rationale: "A linha da guideline para relatorio descreve a âncora como 'a heading word... quando presente', e o único disagreement real e direto entre as duas anotações independentes desta rodada (relatorio_inicio) resolveu a favor de excluir o numeral, por ser mais fiel à descrição literal da guideline (a palavra do cabeçalho, não a numeração formal que a precede). Como este mesmo documento tem duas seções numeradas com romanos no mesmo padrão estrutural (I - RELATÓRIO, II - FUNDAMENTAÇÃO, III - DISPOSITIVO), aplicar convenções diferentes a cada uma introduziria inconsistência de rotulagem sem justificativa textual -- a mesma lógica que motivou a decisão análoga em 2cjjig (adotar a mesma leitura de fronteira para documentos do mesmo formato estrutural), aqui aplicada dentro do mesmo documento em vez de entre documentos."
---

# Decisão: numerais romanos de seção ficam fora das âncoras de heading

`relatorio_inicio`, `capitulo_merito_inicio` e `capitulo_merito_fim` em
doc_6b714f65 adotam a palavra-âncora sozinha ('RELATÓRIO',
'FUNDAMENTAÇÃO', 'DISPOSITIVO'), sem o numeral romano de seção que a
precede no texto ('I -', 'II -', 'III -') -- por consistência interna do
documento e fidelidade à descrição da guideline.
