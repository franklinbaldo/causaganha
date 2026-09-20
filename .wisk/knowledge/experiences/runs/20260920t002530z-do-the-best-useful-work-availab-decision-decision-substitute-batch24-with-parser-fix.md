---
type: "RunDecision"
id: "run-decisions/20260920t002530z-do-the-best-useful-work-availab/decision-substitute-batch24-with-parser-fix"
run: "runs/20260920T002530Z-do-the-best-useful-work-available-in-this-reposi"
question: "Apos supervisionar a PR #1586 (lote 23) até mesclagem, o goal desta rodada previa tambem ingerir um lote 24 real. A PR #1586 documentou (mas nao corrigiu) um bug real de codigo em segmenter_dataset.store._text_element_to_labels (classe de risco 17: um label singleton aninhado dentro de um papel de par inicio/fim e descartado silenciosamente na leitura, contornado apenas por reposicionamento de dados em 3 documentos). Dado o tempo restante desta rodada, qual e o avanco de maior valor: ingerir mais um lote de dados via workaround, ou corrigir a causa raiz no parser?"
decision: "Corrigir a causa raiz no parser (PR #1588, RED->GREEN) em vez de ingerir o lote 24. A correcao beneficia todos os lotes futuros (nao apenas o proximo) e remove a necessidade do workaround de reposicionamento de tags para qualquer documento futuro que tenha esse formato -- avanco estrutural maior do que mais 6 documentos no corpus."
rationale: "Nenhum outro chamador de _PAIR_ROLES existe no repositorio (grep confirmado) -- correcao unica e completa. RED test reproduziu o bug exatamente como descrito na PR #1586 antes da correcao (2 de 3 labels recuperados); GREEN apos o fix, com toda a suite tests/segmenter_dataset (173 documentos reais) verde localmente antes do push."
goal: "goal-batch23-merge-and-batch24"
---

# RunDecision
