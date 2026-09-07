---
goal: "Corrigir AlertBanner.svelte para que o atributo role (alert vs note) reaja de fato a mudancas nas props level/live numa instancia viva, em vez de congelar o valor inicial"
id: "run-goals/20260907t112418z-fa-a-o-melhor-avan-o-poss-vel-n/goal-fix-alertbanner-reactivity"
kind: "task-advance"
rationale: "npm test no web/ (via 'npm run lint'/'npm test' locais, mesmos comandos do job CI 'web') reportou avisos do compilador Svelte 5 'state_referenced_locally' em AlertBanner.svelte:13 apontando que isLive so capturava o valor inicial de live/level; isLive era um 'const' calculado uma vez no corpo do script a partir de props reativas (()), entao um consumidor que reusa a mesma instancia e atualiza level/live (padrao comum ao trocar de estado num banner de alerta) nunca veria role mudar de note para alert nem o inverso -- bug real de acessibilidade/reatividade, nao apenas cosmetico"
run: "runs/20260907T112418Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
status: "achieved"
success_signal: "Teste novo web/src/components/AlertBanner.reactivity.test.ts fica RED antes da correcao (rerender com level/live diferentes nao muda o role renderizado) e GREEN depois (isLive vira $derived); suite completa do web (npm test) permanece verde (489/489, antes 487/487) e 'npx astro check' continua 0 erros"
type: "RunGoal"
---

# RunGoal
