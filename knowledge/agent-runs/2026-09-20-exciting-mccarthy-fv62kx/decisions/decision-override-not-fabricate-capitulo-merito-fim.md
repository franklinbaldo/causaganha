---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-fv62kx-decision-override-not-fabricate-capitulo-merito-fim"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
question: "Dois pares capitulo_merito (TJMA/42725100 'passo a decidir', TJBA/574460088 'Decido.') ficaram sem fechamento -- o raciocinio flui direto para um dispositivo_abertura ja tagueado. Declarar --allowed-unmatched-overrides ou fabricar uma tag <fim> na fronteira do dispositivo_abertura?"
choice: "Declarar --allowed-unmatched-overrides para os dois casos, em vez de fabricar uma tag <fim> na fronteira do dispositivo_abertura ja tagueado."
rationale: "Nenhum documento do corpus (179 documentos antes deste lote) tem um par capitulo_merito fechado com sucesso -- e uma categoria explicitamente listada no guideline como frequentemente ausente por inteiro. Sem precedente de como um <fim> real deveria ser formado neste ponto, e com o guideline explicito em outro lugar (ementa) de nao fabricar fechamento so porque o texto continua, o override documentado e mais fiel ao principio de RFC 0012 Sec 9 ('risk signal, not auto-rejected') do que inventar uma estrutura nova."
---

# Decisão: override em vez de fabricar `capitulo_merito_fim`

Ambos os casos (TJMA/42725100 "passo a decidir", TJBA/574460088
"Decido.") fluem diretamente para um `dispositivo_abertura` já
corretamente tagueado, sem nenhuma frase de transição própria entre os
dois. A tabela do guideline lista "DISPOSITIVO / início do dispositivo"
como o fechamento esperado de `capitulo_merito`, mas isso descreveria
tagear exatamente o mesmo span que `dispositivo_abertura` já cobre —
um padrão de dupla-tag sem qualquer precedente nos 179 documentos
existentes do corpus. Optamos por declarar o override (com a razão
verificada contra o texto-fonte bruto de cada documento) em vez de
inventar essa estrutura nova sem base em nenhum exemplo já validado.
Uma rodada futura que veja `capitulo_merito` fechado com sucesso em um
documento real deve revisar esta decisão.
