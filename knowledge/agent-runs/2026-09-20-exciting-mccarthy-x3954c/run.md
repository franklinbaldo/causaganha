---
type: AgentRun
id: "2026-09-20-exciting-mccarthy-x3954c"
started_at: "2026-09-20T19:24:00Z"
completed_at: "2026-09-20T19:56:00Z"
branch_at_start: "claude/exciting-mccarthy-x3954c"
commit_at_start: "ad49efcf8d278499fab290908b2d3547b3f21552"
claude_md_reading_id: "2026-09-20-exciting-mccarthy-x3954c-reading-claude-md"
issues_reading_id: "2026-09-20-exciting-mccarthy-x3954c-reading-issues"
prs_reading_id: "2026-09-20-exciting-mccarthy-x3954c-reading-prs"
okf_reading_id: "2026-09-20-exciting-mccarthy-x3954c-reading-okf"
goal_ids:
  - "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
primary_goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
considered_work:
  - "#1471 (validar piloto TJRO 2026): bloqueada por credenciais IA ausentes, reconfirmado (>=11a rodada consecutiva) -- nao acionavel."
  - "#1470 (auditoria de catalogo Parquet/CNJ): ja atualizada pela rodada imediatamente anterior (11->61 arquivos, 20/09), sem proximo passo obvio sem reler toda a evidencia -- nao selecionada para nao duplicar/retrabalhar as costas de outra sessao sem necessidade clara."
  - "PR #1597 (correcao dos achados do Codex sobre o lote 25 de #1050): PR ja aberta e com trabalho de codigo feito por sessao concorrente (branch claude/exciting-mccarthy-hyn45b), CI pendente no momento da leitura, sem conflito de merge -- so falta rotina externa (CI + merge). Push la violaria a politica de branch desta sessao (push exclusivo a claude/exciting-mccarthy-x3954c); nao selecionada."
  - "Novo lote real de ingestao para #1050 (padrao das ~25 rodadas anteriores): descartado como PRIMEIRO passo desta rodada porque o proprio script de verificacao pre-lote (scripts/segmenter_governance_status.py) estava travado (ver selected_work) -- ingerir um lote novo sem conseguir verificar governance status/dedup contra o corpus inteiro teria sido exatamente o erro que a licao do batch24 (near-duplicate reintroduzido) ja documentou."
  - "Corrigir o gargalo O(n^2) sem poda em segmenter_dataset.dedup.find_near_duplicates (chamado por splits.build_groups sobre o corpus inteiro): selecionado -- descoberto ao vivo como bloqueio real e imediato ao proximo passo natural de #1050, com caminho de execucao TDD completo (RED/GREEN) e sinal de sucesso observavel dentro do escopo desta sessao, sem depender de credenciais externas nem de branches alheios."
selected_work: "Diagnosticar por que scripts/segmenter_governance_status.py trava por minutos sobre o corpus real de 191 documentos (regressao nunca antes notada em ~25 relatorios anteriores), isolar a causa raiz em segmenter_dataset.dedup.find_near_duplicates (comparacao all-pairs sem poda, chamada por splits.build_groups sobre o store inteiro), escrever testes RED que provem a ausencia de poda, implementar uma poda matematicamente segura (limite de comprimento + quick_ratio), levar os testes a GREEN, e medir o ganho de desempenho real no corpus de producao."
expected_behavior: "Ver success_signal em goal-dedup-quadratic-fix."
entry_state: "new"
target_state: "green"
decision_ids:
  - "2026-09-20-exciting-mccarthy-x3954c-decision-do-not-touch-pr-1597-branch"
  - "2026-09-20-exciting-mccarthy-x3954c-decision-length-bound-not-embedding-or-sampling"
  - "2026-09-20-exciting-mccarthy-x3954c-decision-preserve-insertion-order-for-asymmetric-ratio"
evidence_ids:
  - "2026-09-20-exciting-mccarthy-x3954c-evidence-red-test-unpruned-matcher-count"
  - "2026-09-20-exciting-mccarthy-x3954c-evidence-green-dedup-tests"
  - "2026-09-20-exciting-mccarthy-x3954c-evidence-runtime-measurement"
  - "2026-09-20-exciting-mccarthy-x3954c-evidence-pr-1598-opened"
check_ids:
  - "2026-09-20-exciting-mccarthy-x3954c-check-ruff"
  - "2026-09-20-exciting-mccarthy-x3954c-check-pytest-segmenter-dataset"
  - "2026-09-20-exciting-mccarthy-x3954c-check-governance-status-runtime"
  - "2026-09-20-exciting-mccarthy-x3954c-check-pytest-full-suite"
  - "2026-09-20-exciting-mccarthy-x3954c-check-okf-parser"
  - "2026-09-20-exciting-mccarthy-x3954c-check-agent-run-completeness-final"
result_state: "review"
result_summary: "Corrigido um gargalo O(n^2) sem poda em segmenter_dataset.dedup.find_near_duplicates (chamado por splits.build_groups sobre o corpus inteiro do segmentador, nao um lote), descoberto ao vivo ao tentar rodar scripts/segmenter_governance_status.py -- o primeiro passo padrao de ~25 rodadas anteriores antes de cada lote de #1050 -- que travou por >8min de CPU a 99.9% sobre o corpus real de 191 documentos (18.145 pares, ~27ms/par medido, ~493s projetado so nessa etapa). A correcao poda pares usando dois limites superiores comprovaveis (limite matematico de comprimento derivado de ratio()=2*M/T; quick_ratio() do proprio SequenceMatcher), sem trocar o algoritmo de similaridade (RFC 0012 Sec 10 exige SequenceMatcher/stdlib, nao embeddings) e sem risco de falso-negativo. TDD completo: teste RED (test_find_near_duplicates_never_builds_a_matcher_for_length_incompatible_pairs) provou ausencia de poda na implementacao original (120/120 pares instanciavam SequenceMatcher mesmo quando 64 eram matematicamente impossiveis); apos a correcao, GREEN, mais um segundo teste de equivalencia com uma implementacao de referencia brute-force em 5 thresholds (0.5/0.7/0.85/0.9/0.95) sobre corpus sintetico, garantindo que a poda nunca muda o conjunto de pares reportado. Durante a implementacao, o proprio teste de equivalencia pegou um bug real introduzido pela primeira versao da poda: ordenar candidatos por comprimento trocava silenciosamente qual texto e 'a' vs 'b' no SequenceMatcher, e ratio() nao e garantidamente simetrico -- corrigido preservando a ordem de insercao original so na hora de montar cada par (decision-preserve-insertion-order-for-asymmetric-ratio). Medicao real no corpus de producao: scripts/segmenter_governance_status.py foi de um hang de >8min (so na etapa de dedup) para 1m6.470s completo (todo o script, incluindo I/O de 191+244+31 arquivos e duas chamadas a assign_splits), com saida identica (document_count=191, annotation_count=244, val_ceiling=test_ceiling=29 -- os mesmos numeros que a PR #1597 ja documentava para o estado pos-lote-25). uv run ruff check/format --check limpos sobre o repositorio inteiro; uv run pytest -q tests/segmenter_dataset 100% verde; uv run pytest -q (suite completa) sem nenhuma falha fora do proprio gate de completude deste relatorio (esperado em rascunho, resolvido ao preencher completed_at); uv run okf-parser check knowledge --relational-schema okf.schema.sql conformant, 0 diagnosticos. PR #1597 (trabalho de outra sessao sobre o mesmo #1050) foi deliberadamente deixada intocada -- ver decision-do-not-touch-pr-1597-branch."
next_move: "PR #1598 aberta (https://github.com/franklinbaldo/causaganha/pull/1598), sessao inscrita em sua atividade (subscribe_pr_activity) para conduzi-la ao merge. Uma rodada futura deve: (1) reconfirmar #1598 mesclada; (2) reconfirmar PR #1597 mesclada (o hyn45b branch alheio, so faltava CI+merge de rotina no momento desta leitura); (3) reconfirmar ao vivo scripts/segmenter_governance_status.py -- agora rapido (~1min) -- antes de selecionar o proximo lote de #1050 (document_count=191, val_ceiling=test_ceiling=29, ainda abaixo do piso RFC 0012 Sec 5 item 4 de >=30 cada; falta ~1 lote deste tamanho); (4) considerar se o mesmo padrao de poda por limite de comprimento vale a pena generalizar para scripts/segmenter_semantic_audit.py ou outros pontos que tambem possam fazer comparacao all-pairs sobre o corpus inteiro (nao investigado nesta rodada, escopo ficou deliberadamente restrito a find_near_duplicates); (5) a tensao AgentRun-vs-Wisk continua sem reconciliacao do dono humano (ja escalada em 2026-09-14) -- nao reescalar sem fato novo."
---

# Agent run

Rodada de continuidade sobre a linhagem #1050 (corpus real do
segmentador, RFC 0012). Ao tentar rodar
`scripts/segmenter_governance_status.py` -- o primeiro passo padrao de
~25 rodadas anteriores antes de selecionar o proximo lote -- o processo
ficou preso por mais de 8 minutos de CPU a 99.9% sobre o corpus real de
191 documentos, um comportamento nunca antes relatado (todo relatorio
anterior descreve a chamada como instantanea). Investigacao ao vivo
isolou a causa em `segmenter_dataset.dedup.find_near_duplicates`:
`splits.build_groups` a chama sobre o store inteiro fazendo
`SequenceMatcher.ratio()` completo para cada um dos 18.145 pares
possiveis (~27ms/par medido, ~493s so nessa etapa) -- exatamente o uso
que o proprio docstring da funcao ja advertia contra ("nao destinado a
comparacao all-pairs em escala de corpus"), mas que e o unico uso real
em producao. Esta rodada trata a correcao desse gargalo, com TDD
completo, como o avanco mais valioso e imediatamente acionavel
disponivel -- sem ele, nenhum lote futuro de #1050 pode ser verificado
com seguranca contra reintroducao de near-duplicates (a mesma classe de
erro ja documentada no batch24).
