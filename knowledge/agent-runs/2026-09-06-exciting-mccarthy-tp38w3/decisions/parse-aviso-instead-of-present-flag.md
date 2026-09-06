---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-tp38w3-decision-parse-aviso-instead-of-present-flag"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
question: "Como o snapshot decide se uma fonte está 'indisponível' (não deve ser comparada) em vez de apenas 'ausente' (nunca teve registro), já que ProcessoResultado.djen/juris/stj/datajud só expõem um booleano `present` que já vem `false` nos dois casos?"
choice: "Detectar indisponibilidade a partir de ProcessoResultado.avisos, reaproveitando o formato já existente e testado formatFonteIndisponivelAviso('<fonte>', detalhe) (introduzido por #1107/PR#1159). Em vez de duplicar esse parsing como uma regex solta em consultationSnapshot.ts, foi adicionada uma função irmã parseFonteIndisponivelAviso() em processoCnj.ts — o inverso exato do formatter — mantendo formato e parsing como uma dupla nomeada e testável no mesmo módulo que já é a autoridade sobre esse texto, em vez de duas cópias divergentes."
rationale: "Reusar o vocabulário de avisos já produzido pelo caminho de produção real (queryRowSafe) é mais confiável do que inventar um segundo sinal: nenhuma mudança de contrato é necessária em ProcessoResultado, e o parsing simétrico ao formatter evita que os dois textos divirjam silenciosamente no futuro (o mesmo raciocínio que already levou #1107 a extrair formatFonteIndisponivelAviso como função nomeada em vez de string inline)."
---

# Decisão: detectar indisponibilidade via avisos, não via um novo campo

`present=false` sozinho não distingue "nunca registrado" de "registrado mas falhou ao ler agora". A rodada resolveu isso lendo `ProcessoResultado.avisos` com um parser simétrico ao formatter já existente, em vez de adicionar um campo novo ao contrato de `buscarProcesso()`.
