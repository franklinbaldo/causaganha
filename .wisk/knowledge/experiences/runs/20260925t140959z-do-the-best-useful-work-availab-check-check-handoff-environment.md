---
type: "RunCheck"
id: "run-checks/20260925t140959z-do-the-best-useful-work-availab/check-handoff-environment"
run: "runs/20260925T140959Z-do-the-best-useful-work-available-in-this-reposi"
kind: "handoff-environment"
procedure: "git rev-parse HEAD; git branch --show-current; git status --porcelain; ls .wisk (checkar manifest.json/specs/ ausentes = checkout novo); env | grep -iE '^(IAS3_|IA_ACCESS|IA_SECRET)'; ls ~/.config/internetarchive/ia.ini"
result: "Checkout novo confirmado: .wisk/manifest.json e .wisk/specs/ (estado gerado, gitignored) estavam ausentes -- 'wisk start' quebrou com 'RunSpec not found: run-specs/experience' ate 'wisk init .' ser rodado, restaurando o bundle gerenciado (54 arquivos gerenciados, 1479 preservados). O LoopRun retomado (140959Z) tem baseline de um container anterior totalmente diferente: branch claude/exciting-mccarthy-cw428g @ fb263bdbbf1d (dirty=true) contra o estado real deste container -- branch claude/exciting-mccarthy-2lnbo3 @ 06dc3c420b1a (limpo antes desta rodada comecar a editar). Sem credenciais IA no ambiente (mesma reconfirmacao de sempre). O baseline do handoff esta desatualizado (container/branch trocados), mas o handoff em si (bloqueio de credencial #1471) segue descrevendo o estado real -- tratado abaixo em check-handoff-disposition."
status: "pass"
evidence: "run-evidence/20260925t140959z-do-the-best-useful-work-availab/evidence-wisk-init-required"
---

# RunCheck
