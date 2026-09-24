---
type: AgentGoal
id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal: "Eliminar o gargalo O(n^2) de comparacao all-pairs sem poda em segmenter_dataset.dedup.find_near_duplicates, que faz scripts/segmenter_governance_status.py (chamado antes de cada lote de #1050 via splits.build_groups) levar minutos num corpus de 191 documentos, sem alterar o conjunto de pares near-duplicate que a funcao reporta."
rationale: "#1050 e a linhagem mais ativa do repositorio (25 lotes reais mesclados, document_count 61->191) e sua propria infraestrutura de verificacao (governance status, chamado antes/depois de cada lote ha ~25 rodadas) parou de ser praticavel exatamente por causa do crescimento que a issue pede -- um bloqueio real ao proximo passo natural, descoberto ao vivo (nao estava em nenhuma issue aberta). O modulo dedup.py ja documentava o risco em sua propria docstring ('nao destinado a comparacao all-pairs em escala de corpus'), mas segmenter_dataset.splits.build_groups o chama exatamente assim sobre o store inteiro -- um descompasso entre contrato documentado e uso real que so ficou caro o suficiente para notar agora."
success_signal: "uv run python scripts/segmenter_governance_status.py roda em segundos (nao minutos) sobre o corpus real de 191 documentos, com a mesma saida JSON (document_count/val_ceiling/test_ceiling identicos); um teste novo (test_find_near_duplicates_matches_brute_force_across_thresholds_and_lengths) prova que a poda nunca muda o conjunto de pares reportado comparando contra uma implementacao de referencia O(n^2) sem poda, em varios thresholds; um segundo teste novo (test_find_near_duplicates_never_builds_a_matcher_for_length_incompatible_pairs) prova via contagem que pares comprovadamente incompativeis por tamanho nunca chegam a instanciar SequenceMatcher; toda a suite tests/segmenter_dataset continua 100% verde; ruff check/format --check limpos."
status: "achieved"
---

# Goal: eliminar gargalo quadratico em find_near_duplicates

Ao tentar rodar `scripts/segmenter_governance_status.py` como primeiro
passo antes de selecionar o proximo lote de #1050 (pratica padrao de
~25 rodadas anteriores), o processo ficou preso a 99.9% de CPU por mais
de 8 minutos sem produzir saida -- muito acima do comportamento
historico ("confirmado ao vivo" instantaneo em todo relatorio anterior
desde o batch1). Isso bloqueia o proprio mecanismo de verificacao que
cada lote de #1050 depende, e so vai piorar conforme o corpus continua
crescendo em direcao ao piso RFC 0012 Sec 5 item 4 (>=200 documentos).

Investigacao ao vivo (profiling isolado, medicao de amostra de pares)
confirmou a causa raiz: `segmenter_dataset.splits.build_groups` chama
`segmenter_dataset.dedup.find_near_duplicates` sobre TODOS os
documentos do store (nao um lote), e essa funcao fazia
`SequenceMatcher.ratio()` completo para cada um dos 18.145 pares
possiveis em 191 documentos, a ~27ms/par medido -- ~493s so nessa
etapa. O proprio docstring de `find_near_duplicates` ja avisava contra
esse uso ("nao destinado a comparacao all-pairs em escala de corpus"),
mas o unico chamador real (`build_groups`, usado por `assign_splits`,
usado por `segmenter_governance_status.py` e pelo comando real
`segmenter_dataset assign-splits`) faz exatamente isso -- um
descompasso entre contrato documentado e uso de producao.
