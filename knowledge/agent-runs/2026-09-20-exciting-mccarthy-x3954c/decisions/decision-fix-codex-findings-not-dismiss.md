---
type: AgentDecision
id: "2026-09-20-exciting-mccarthy-x3954c-decision-fix-codex-findings-not-dismiss"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
question: "O bot chatgpt-codex-connector sinalizou 3 achados distintos (2x P2 duplicado sobre length_a==0/threshold<=0, 1x P1 sobre arredondamento de ponto flutuante na fronteira exata do threshold, 1x P2 sobre ordem de pares com ratio empatado) na PR #1598 logo apos ela ser aberta. Cada um e um bug real ou uma reclamacao cosmetica que pode ser ignorada?"
choice: "Tratar os tres como bugs reais e corrigir todos, com teste RED contra a implementacao anterior antes de cada correcao. Nenhum foi dispensado."
rationale: "Verificacao ao vivo confirmou cada achado: (1) threshold=0 (aceito por SplitManifest._validate_ratios) e o caso de duas strings vazias colidindo (ratio=1.0) ambos retornavam [] em vez do conjunto correto de pares -- quebra de contrato explicito da propria funcao (docstring anterior nao excluia esses casos); (2) 'aa' vs 'aaa' em threshold=0.8 tem ratio() EXATO 0.8, mas a formula anterior (la*(2-threshold)/threshold) computava 2.9999999999999996 em vez de 3.0 por erro de arredondamento de ponto flutuante, descartando um near-duplicate real -- exatamente o tipo de falso-negativo que o goal desta rodada prometia nunca introduzir; (3) o exemplo de 3 documentos do proprio Codex reproduziu ao vivo uma ordem diferente da implementacao de brute-force para pares com ratio empatado, contradizendo a alegacao explicita do meu proprio docstring/PR de equivalencia total com o scan ingenuo. CLAUDE.md nao lista uma regra especifica para achados de bots de review, mas a diretriz geral do repositorio (TDD como fluxo padrao, testes como contrato da mudanca) e a garantia central do proprio goal desta rodada (zero falso-negativo) tornam obrigatorio tratar qualquer achado que demonstre um caso onde a saida muda como um bug, nao como uma nitpick estilistica."
---

# Decisão: corrigir, não dispensar, os 3 achados do Codex

A revisão automática (`chatgpt-codex-connector[bot]`) rodou assim que a
PR #1598 foi aberta e sinalizou 4 comentários de review (2 duplicados
sobre o mesmo bug):

1. **P2 (x2, duplicado)** — `length_a == 0 or threshold <= 0: continue`
   descarta pares que o contrato anterior aceitava (duas strings vazias
   têm ratio 1.0; `threshold=0` deveria unir todos os pares, já que todo
   ratio é `>= 0`, e `SplitManifest._validate_ratios` aceita 0
   explicitamente).
2. **P1** — a fórmula `la*(2-threshold)/threshold` comparada com `lb`
   pode arredondar para o lado errado exatamente na fronteira do
   threshold (`"aa"` vs `"aaa"`, threshold 0.8, ratio real 0.8 —
   confirmado ao vivo: a fórmula antiga produz `2.9999999999999996` em
   vez de `3.0`, descartando o par).
3. **P2** — a travessia em ordem de comprimento muda a ordem relativa
   de pares com ratio empatado em relação ao scan ingênuo em ordem de
   inserção, mesmo com a correção de simetria já aplicada
   anteriormente nesta rodada (`decision-preserve-insertion-order-for-asymmetric-ratio`)
   — essa correção resolveu qual texto é `a` vs `b` na comparação, mas
   não a ordem de *descoberta* dos pares usada como desempate por
   `sorted(..., reverse=True)` (estável).

Cada achado foi reproduzido com um teste RED antes de qualquer mudança
de código (ver `evidence-red-tests-codex-findings`), confirmando que
não são falsos positivos do bot. A correção final substitui a fórmula
de divisão por uma comparação direta e matematicamente equivalente sem
divisão (`2*length_a >= threshold*(length_a+lengths[j])`), que resolve
os três problemas ao mesmo tempo: elimina o arredondamento da divisão,
generaliza corretamente para `length_a=0`/`threshold<=0` sem
caso-especial, e o desempate de ordem foi resolvido separadamente
ordenando o resultado final por `(insertion_index[a], insertion_index[b])`
antes do sort estável por ratio.
