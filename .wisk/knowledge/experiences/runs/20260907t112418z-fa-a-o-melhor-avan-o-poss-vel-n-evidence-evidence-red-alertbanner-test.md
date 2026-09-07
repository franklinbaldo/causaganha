---
type: "RunEvidence"
id: "run-evidence/20260907t112418z-fa-a-o-melhor-avan-o-poss-vel-n/evidence-red-alertbanner-test"
run: "runs/20260907T112418Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "execution"
reference: "local: cd web && npx vitest run src/components/AlertBanner.reactivity.test.ts (antes da correcao, isLive como const)"
summary: "RED confirmado: os 2 testes falharam. 'switches role from note to alert when level changes' -- getByRole('alert') nao encontrou elemento apos rerender com level='error' (role continuou 'note'). 'switches role from alert to note when live is toggled off' -- getByRole('note') falhou de forma simetrica. Ambos porque isLive era um 'const' calculado uma vez a partir de live/level no momento da inicializacao."
goal: "goal-fix-alertbanner-reactivity"
---

# RunEvidence
