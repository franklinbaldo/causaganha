---
type: AgentGoal
id: "2026-09-20-exciting-mccarthy-6nbygb-goal-verify-and-merge-1590-1591"
run_id: "2026-09-20-exciting-mccarthy-6nbygb"
goal: "Reverificar de forma independente e mesclar as PRs #1590 (lote 24 real para #1050) e #1591 (bookkeeping Wisk), ambas ja verdes/limpas com achados de review ja endereçados por uma sessao anterior"
rationale: "Continuidade e entrega: duas PRs prontas (11/10 checks verdes, mergeable_state=clean, 7 review threads do Codex ja resolvidos com correcoes verificadas contra o texto-fonte) estao sentadas sem merge. Deixa-las abertas enquanto uma nova rodada comeca um lote 25 arriscaria um novo conflito de merge em knowledge/backlog/issue-1050.md (exatamente o que a PR #1591 ja teve que resolver uma vez nesta madrugada). O precedente do proprio pipeline (ex: rodada ejibsp, 2026-09-05) e mesclar autonomamente apos reverificacao independente quando o merge esta limpo e os checks estao verdes -- nao esperar passivamente por um humano."
success_signal: "Verificacao independente (nao apenas o autorrelato das sessoes anteriores) confirma: fidelidade verbatim dos 5 documentos novos de #1590 contra o parser real, scripts/segmenter_governance_status.py com document_count/val_ceiling/test_ceiling coerentes com o que a PR reivindica, uv run ruff check/format e pytest -q tests/segmenter_dataset verdes no branch de #1590. Apos essa verificacao, #1590 e mesclada (merge_pull_request), seguida por #1591 (rebase/atualizada contra o novo main se necessario), com ambos os merges confirmados via pull_request_read apos o fato."
status: "in_progress"
---

# Goal: reverificar e mesclar #1590 e #1591

Antes de abrir um lote 25 novo para #1050, fechar o trabalho ja pronto:
duas PRs verdes, sem review pendente, aguardando so a decisao de
merge. A verificacao independente cobre exatamente as mesmas dimensoes
que toda rodada anterior desta linhagem cobriu (fidelidade verbatim,
governanca do corpus, ruff, pytest) para nao confiar cegamente no
autorrelato de PRs geradas por outra sessao.
