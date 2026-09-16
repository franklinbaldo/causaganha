---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-c4y4rc-reading-okf"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, knowledge/agent-runs/2026-09-15-exciting-mccarthy-2hb3sq/ (rodada mais recente mesclada), knowledge/backlog/issue-1051.md, docs/rfc/0012-segmenter-dataset-confiavel-baseline.md §5 item 4, src/segmenter_dataset/splits.py::assign_splits"
finding: "Tensão AgentRun-vs-Wisk inalterada (Wisk `uv run wisk start` -> blocked/no-eligible-session, hourly-loop.md/index.md seguem declarando AgentRun legado sem ressalva) -- sigo o precedente de 5+ rodadas anteriores: obedecer ao prompt agendado, sem nova notificação. Achado NOVO desta rodada, verificado ao vivo: mesmo com o pool de 61 documentos 100% adjudicado, assign_splits (ratio-based sobre o total do corpus, não sobre o pool elegível) produz no máximo val=9/test=9 -- muito abaixo do piso de RFC 0012 §5 item 4 (>=30 cada). Continuar #1051 sozinha (adjudicar mais documentos dentro do pool atual de 61) não pode atingir a meta; é preciso crescer o corpus total (#1050) para a ordem de ~200 documentos, que é exatamente o que a própria RFC embute nas metas (150+30+30=210 ~ as proporções 70/15/15 já usadas)."
---

# Leitura: conhecimento OKF relevante

1. **Tensão AgentRun-vs-Wisk**: `knowledge/agent-runs/index.md` e
   `.claude/hourly-loop.md` continuam declarando, sem ressalva, que o
   mecanismo `AgentRun` é legado e que o loop horário real usa
   exclusivamente Wisk. `uv run wisk start` retornou
   `{"state": "blocked", "blockers": ["no-eligible-session"]}` — mesmo
   resultado de toda rodada anterior desde pelo menos 14/09. Nada mudou
   desde a última avaliação (2hb3sq). Sigo o mesmo precedente de 6+ rodadas
   consecutivas: obedecer à instrução explícita do prompt agendado (que
   pede o scaffold `AgentRun`), sem enviar nova notificação proativa —
   nenhum fato novo justificaria repetir um alerta já enviado sem resposta.

2. **Rodada anterior mesclada (2hb3sq, PR #1533/38a3116)**: escalou
   `review_count`/`evaluation_eligible_count` de 29 para 31, cruzando pela
   primeira vez o piso *combinado* de RFC 0012 §5.4 (>=30). Seu próprio
   `next_move` já avisava: "isso é o total combinado -- val e test
   precisam >=30 cada, então o trabalho de #1051 não está esgotado; uma
   rodada futura deve verificar quantos dos 31 documentos
   evaluation-eligible caem em cada split... antes de assumir que o piso
   real (por split) já foi atingido."

3. **Verificação ao vivo desta rodada** (`uv run python -m
   segmenter_dataset assign-splits --data-root data/segmenter --output
   /tmp/scratch_split_manifest.json --seed 0`): com o estado real do store
   (61 documentos, 31 evaluation-eligible), o comando produz
   `train=43 val=9 test=9`. Lendo `assign_splits`
   (`src/segmenter_dataset/splits.py:265`), os alvos são
   `val_target = round(total_eligible * val_ratio)` e
   `test_target = round(total_eligible * (1 - train_ratio - val_ratio))`,
   onde `total_eligible` é o total de documentos com pelo menos uma
   anotação (train_eligible ∪ evaluation_eligible) — **não** o tamanho do
   pool elegível para avaliação. Com `val_ratio=test_ratio=0.15` e um
   corpus de 61 documentos, o teto é `round(61*0.15)=9` **mesmo que todos
   os 61 documentos fossem adjudicados hoje** (recomputei substituindo
   `evaluation_eligible=train_eligible` inteiro: mesmo `val=9/test=9`).
   Isso confirma matematicamente o aviso do `next_move` de 2hb3sq: o piso
   de RFC 0012 §5 item 4 (>=30 val, >=30 test, ambos adjudicados) é
   **estruturalmente inatingível** enquanto o corpus total ficar em ~61
   documentos, não importa quanta adjudicação aconteça dentro dele.

4. **Releitura de RFC 0012 §5 item 4** ("Metas de suprimento do primeiro
   release: >= 150 docs de treino anotados... >= 30 de validação
   adjudicados, >= 30 de teste adjudicados"): 150+30+30=210, e
   150/210≈71.4%, 30/210≈14.3% — quase exatamente as proporções
   `train_ratio=0.70`/`val_ratio=0.15` já hardcoded em
   `assign_splits_command`. Ou seja, a própria RFC já pressupõe um corpus
   total na casa de ~200 documentos para essas proporções produzirem
   30/30 reais; o gargalo nunca foi "adjudicar o que já existe" (#1051
   isoladamente), é "crescer o corpus total" (#1050, issue-mãe sem nenhum
   comentário até agora, nunca trabalhada diretamente por esta linhagem).

5. **`knowledge/backlog/issue-1051.md`** segue desatualizado (`status:
   "blocked"`, `last_verified_at: 2026-09-07T02:45:00Z`), como já
   apontado por 2 rodadas anteriores (wvzu11, 2hb3sq) sem correção —
   candidato a corrigir nesta rodada junto com o achado acima, para não
   deixar a lacuna de leitura se repetir indefinidamente.
