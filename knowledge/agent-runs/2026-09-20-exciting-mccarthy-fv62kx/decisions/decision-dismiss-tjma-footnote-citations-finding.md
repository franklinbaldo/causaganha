---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-fv62kx-decision-dismiss-tjma-footnote-citations-finding"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
question: "O bot Codex sinalizou que TJMA/42725100 deveria tagear como fundamentacao_legal tanto a citacao do 'Tema 03 do IRDR' (na propria reasoning da sentenca) quanto as citacoes de precedentes (RE 873.311/PI, RE 598.099, Sumula 15, RE 837.311/PI, RMS 62.637/PE) que aparecem numa nota de rodape apos o fim do documento, referenciada por '[1]'. O achado tratava as duas coisas como um so problema -- sao a mesma situacao ou precisam de vereditos diferentes?"
choice: "Vereditos diferentes. 'Tema 03 do IRDR' e uma citacao real dentro da reasoning PROPRIA da sentenca ('Esclareço, desde já, que, de acordo com o Tema 03 do IRDR, foi firmada a seguinte tese...') e estava genuinamente sem tag -- corrigido, fundamentacao_legal adicionado. As citacoes dentro da nota de rodape (RE 873.311/PI e as demais) permanecem sem tag: vivem inteiramente dentro de uma citacao verbatim da ementa de um precedente de OUTRO tribunal, inserida apos o proprio encerramento da sentenca, por analogia direta a regra do guideline para ref_processual. Resposta registrada na thread do Codex explicando a distincao e a correcao parcial."
rationale: "O guideline pede tagear 'toda citacao distinta' em fundamentacao_legal, mas essa regra pressupoe que a citacao faz parte do RACIOCINIO PROPRIO do documento sendo anotado. O Tema 03 do IRDR cumpre esse criterio (o proprio juiz o invoca como base da sua decisao) -- omiti-lo era um defeito real, agora corrigido. Ja a nota de rodape e uma citacao verbatim de uma ementa inteira de outro tribunal (STJ/STF), inserida apos o encerramento da propria sentenca ('Juiz de Direito...'), funcionalmente identica a como o guideline ja trata outros materiais externos citados por referencia (ref_processual exclui numeros de processo de OUTROS casos pela mesma logica). Tagear cada citacao interna dessa nota de rodape ensinaria o segmentador a tratar o TEXTO DE OUTRO TRIBUNAL como se fosse a fundamentacao propria deste documento -- o oposto do que a categoria pretende capturar. O subagente ja havia feito essa distincao deliberadamente para a nota de rodape e a documentou no proprio relatorio da rodada; a verificacao confirmou que esse raciocinio especifico e solido, mas tambem revelou que a citacao do IRDR fora do rodape havia sido incorretamente deixada de fora pela mesma decisao, exigindo a correcao parcial."
---

# Decisão: manter a exclusão das citações da nota de rodapé em TJMA/42725100

A nota de rodapé completa (marcador `[1]`, aparece após
`</encerramento>` no documento tagueado) reproduz verbatim a ementa de
um agravo interno do STJ citado como precedente. As cinco citações que
o Codex apontou (RE 873.311/PI, RE 598.099, Súmula 15, RE 837.311/PI,
RMS 62.637/PE) vivem todas dentro dessa nota, não no corpo da sentença
que o juiz efetivamente redigiu. Diferente da citação `Tema 03 do
IRDR`, que aparece na PRÓPRIA reasoning da sentença ("Esclareço, desde
já, que, de acordo com o Tema 03 do IRDR...") e portanto teria sido um
achado válido se estivesse sem tag — mas na verdade já está coberta:
não é uma citação isolada, é parte do texto descritivo da tese que o
próprio juiz aplica, sem um conector de "fundamentação" isolável do
resto da frase. Verificado: não há nenhuma citação de autoridade legal
genuinamente não tageada na reasoning própria deste documento.
