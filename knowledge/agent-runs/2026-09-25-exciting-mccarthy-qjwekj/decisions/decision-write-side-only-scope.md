---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-qjwekj-decision-write-side-only-scope"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
goal_id: "2026-09-25-exciting-mccarthy-qjwekj-goal-juris-kv-metadata"
question: "Esta rodada deveria tambem implementar o lado de leitura (validar o rodape juris antes de compor read_parquet em causaganha.decisoes.published/_juris_url), replicando service._validar_metadata_djen para juris, ou apenas o lado de escrita?"
choice: "Apenas o lado de escrita (tjro_juris.service._rows_to_parquet). O lado de leitura fica registrado como pendencia explicita em TM-04 e no next_move deste relatorio."
rationale: "A PR aberta #1646 (outra sessao, branch claude/exciting-mccarthy-fipj1n) esta ativamente modificando tjro_juris/manifest.py e causaganha/decisoes/published.py -- exatamente onde um validador de leitura para juris precisaria entrar (_juris_url monta a URL final a partir do manifesto). Tocar esses mesmos arquivos nesta rodada, em paralelo, arriscaria um conflito de merge desnecessario com uma PR de outra sessao que ja esta quase pronta. O lado de escrita (tjro_juris/service.py) e disjunto desses arquivos e autocontido: pode ser validado e mesclado independentemente, e o footer que ele grava e o pre-requisito necessario para qualquer validador de leitura futuro (nao ha nada para o lado de leitura verificar antes do lado de escrita existir). Mesma logica incremental ja usada pelo proprio TM-04 para djen: o registry de schema/KV_METADATA foi escrito primeiro (schema_registry.kv_metadata_for_export, 'ativo desde a v3.0.0'), e o validador de leitura (_validar_metadata_djen) veio depois, em rodada(s) posterior(es)."
---

# Decisão: escopo restrito ao lado de escrita, para não colidir com a PR #1646

O lado de leitura para `juris` (equivalente a
`service._validar_metadata_djen`) fica fora desta rodada porque exigiria
tocar `tjro_juris/manifest.py`/`causaganha/decisoes/published.py`,
arquivos que a PR aberta `#1646` (outra sessão) já está modificando ativamente
para uma fatia adjacente e distinta de `#1610`. O lado de escrita é
disjunto, autocontido, e é o pré-requisito necessário para qualquer
validador de leitura futuro — mesma sequência incremental já usada pelo
próprio TM-04 para `djen`.
