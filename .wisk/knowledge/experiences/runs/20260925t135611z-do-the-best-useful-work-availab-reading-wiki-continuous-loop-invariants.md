---
type: "RunReading"
id: "run-readings/20260925t135611z-do-the-best-useful-work-availab/wiki-continuous-loop-invariants"
run: "runs/20260925T135611Z-do-the-best-useful-work-available-in-this-reposi"
kind: "experiences"
subject: "wiki/continuous-loop-operational-invariants"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "Confirma o padrao ja seguido nesta rodada antes de ler o wiki: PR verde pode ficar mergeable_state=behind/bloqueada por um required check (GitGuardian) que so re-dispara em head atualizado -- a acao correta e update_pull_request_branch, nao tratar como travada (linha 19 do wiki). Ja apliquei isso em #1637 (405 por estar behind -> update-branch disparado) antes de ler este registro, entao a leitura confirma em vez de mudar a decisao. Tambem confirma: handoff stale nunca e evidencia mais forte que o estado real observado no resume (o que motivou aceitar/arquivar handoff-pr-1625-awaiting-ci como ja resolvido em vez de reexecutar seu next_action); e que 'wisk init .' e necessario num checkout novo antes de 'wisk start' funcionar (exatamente o bloqueio no-eligible-session/candidates:[] que resolvi nesta sessao antes de achar esta mesma nota ja documentada)."
---

# RunReading
