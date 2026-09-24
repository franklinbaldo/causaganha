---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-mjd1vm-reading-prs"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
subject: "open_prs"
reference: "mcp__github__list_pull_requests (owner=franklinbaldo, repo=causaganha, state=open); pull_request_read get/get_status/get_check_runs/get_review_comments em #1597, #1598, #1599"
finding: "Quatro PRs abertas, tres delas paradas ha exatamente 4 dias (ultima atividade 2026-09-20, hoje e 2026-09-24) sem nenhum commit no repositorio nesse intervalo: #1597 (correcoes Codex do lote 25, ja fisicamente corrigidas em codigo pelo commit 16f6729 mas com as 3 threads de revisao do Codex ainda marcadas nao-resolvidas no GitHub, e mergeable_state=behind por 1 commit docs-only), #1598 (fix de performance O(n^2) em dedup.py, CI 100% verde, 4/4 threads Codex ja resolvidas, mergeable_state=clean) e #1599 (PR do proprio dono humano formalizando a politica de closeout do Wisk, CI verde, sem findings bloqueantes). #1353 (dependabot) fora de escopo. Confirmado nesta leitura: os 3 findings P2 do Codex em #1597 (valor_condenacao indevido em TJCE/363676235, honorarios_fim ancorado em ponto final em vez de frase distintiva em TJCE/363676235 e TJTO/285641901) ja estao corrigidos no conteudo real dos arquivos de anotacao pelo commit 16f6729 -- as threads do GitHub simplesmente nunca foram respondidas/resolvidas."
---

# Leitura: PRs abertas

`mcp__github__list_pull_requests` (state=open) retornou 4 resultados:

- **#1599** ("ops: make Wisk closeouts material and OKF-native") --
  aberta pelo proprio `franklinbaldo` (dono humano), nao por uma sessao
  Claude. Aperta o contrato do loop horario para que o Wisk nao crie
  PRs de closeout so-documentacao depois que trabalho substantivo ja
  mergeou, e para que bloqueios externos repetidos virem estado OKF
  duravel com condicao de reativacao explicita. CI verde
  (`mergeable_state: clean`), Codex revisou sem findings bloqueantes
  (so um aviso de limite de uso). Diretamente relevante para a tensao
  AgentRun-vs-Wisk ja registrada em to0ars (2026-09-14): o proprio dono
  esta ativamente formalizando o mecanismo Wisk, reforcando que nao ha
  fato novo aqui que justifique reescalar -- ele ja esta ciente e
  trabalhando nisso. PR do dono, nao mexida nesta rodada (nao e papel
  desta sessao revisar/mesclar a propria PR do dono).
- **#1598** ("fix(segmenter): eliminate O(n^2) unpruned near-duplicate
  scan in dedup.py") -- autoria Claude (sessao x3954c), branch
  `claude/exciting-mccarthy-x3954c`. Corrige uma trava real e
  confirmada ao vivo (`segmenter_governance_status.py` pendurado 8+ min
  a 99.9% CPU no corpus de 191 documentos) com poda por dois limites
  matematicamente comprovados (bound de comprimento + `quick_ratio()`),
  sem falso-negativo possivel. TDD: teste que falha (RED) contra a
  implementacao original contando construcoes de `SequenceMatcher`,
  teste de equivalencia contra brute-force em 5 thresholds (GREEN).
  11/11 checks verdes, `mergeable_state: clean`, todas as 4 threads de
  revisao do Codex ja `is_resolved: true` (P1 de arredondamento de
  float na fronteira exata do threshold, 2x P2 de pares com
  comprimento/threshold zero, P2 de ordenacao estavel para ratios
  empatados -- todas corrigidas em commits subsequentes da mesma
  sessao antes desta leitura). Pronta para merge humano; nao mesclada
  por esta sessao (ver `decision-do-not-self-merge-other-sessions-prs`).
- **#1597** ("fix(segmenter): address batch25 Codex review findings
  (#1050)") -- autoria Claude (sessao hyn45b), follow-up ao lote 25
  (#1594, mergeado antes do Codex terminar de revisar). Corrigiu 10
  defeitos de cobertura reais no primeiro commit; uma segunda rodada de
  revisao do Codex sobre esse proprio fix encontrou mais 3 defeitos
  (commit 16f6729, ja no branch): `R$ 10.000,00` indevidamente marcado
  `valor_condenacao` num caso `JULGO TOTALMENTE IMPROCEDENTES` (pedido
  negado, nao condenacao), e dois `honorarios_fim` ancorados so num
  ponto final em vez de uma frase distintiva ("valor atualizado da
  causa"/"valor atualizado da condenação"). Verificado ao vivo nesta
  leitura (grep direto nos arquivos de anotacao apos merge do
  worktree): as 3 correcoes estao de fato no conteudo, mas as 3 threads
  do Codex no GitHub continuam `is_resolved: false` -- ninguem clicou
  "Resolve" nem respondeu. Alem disso `mergeable_state: behind` (base
  parado em a914d57, main avancou 1 commit docs-only para ad49efc).
  Nenhuma acao de codigo pendente identificada alem de sincronizar com
  main e fechar as threads -- ver goal desta rodada.

Conclusao: as PRs #1597/#1598 sao exatamente o "trabalho ja iniciado"
que o prompt desta rodada pede para retomar -- ambas na linhagem #1050
ja mapeada, sem bloqueio de credenciais, com CI verde ou quase.
#1597 precisa de trabalho residual (sync com main + fechar threads
ja resolvidas em codigo); #1598 esta pronta, so falta o merge humano.
Nenhuma PR aberta esta vermelha nem tem findings de revisao ainda nao
verificados/corrigidos.
