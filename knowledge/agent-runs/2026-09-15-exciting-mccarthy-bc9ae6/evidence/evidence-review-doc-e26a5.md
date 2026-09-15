---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-bc9ae6-evidence-review-doc-e26a5"
run_id: "2026-09-15-exciting-mccarthy-bc9ae6"
goal_id: "2026-09-15-exciting-mccarthy-bc9ae6-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_e26a555b27c8673a1b990ab286d07107/rev_ea54365ed92bffaa7deaa1637c909353.xml"
summary: "ReviewRecord real adjudicando doc_e26a555b27c8673a1b990ab286d07107 (acórdão TJRO, 1ª Turma Recursal, formato capa+ementa-estruturada) entre a anotação histórica (ann_9e1e5cb9..., família prompt_subagents:haiku, historical_migration:seed) e a nova segunda anotação independente (ann_bb59c432..., família prompt_subagents:general-purpose, seeded_with=none)."
---

# Evidência: adjudicação de doc_e26a555b27c8673a1b990ab286d07107

Disagreements resolvidos, todos a favor da nova anotação, cada um ancorado em texto explícito do guideline v7:

- `resultado`: histórica tagueava "NEGAR PROVIMENTO" dentro do `voto` individual do relator; nova tagueava "RECURSO CONHECIDO E NÃO PROVIDO" dentro do `acordao_decisorio` colegiado. A nota "Acórdão (second-instance) notes" do guideline diz explicitamente que o resultado operativo de um acórdão é o `acordao_decisorio` colegiado, não uma abertura de um `voto` individual -- mesma lógica aplicada a `resultado`. Adotado o span da nova anotação.
- `cabecalho_inicio`: histórica tagueava "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA" (5 palavras); nova tagueava só "PODER JUDICIÁRIO" (2 palavras), igual ao exemplo trabalhado do próprio guideline (`<cabecalho><inicio>PODER JUDICIÁRIO</inicio> Comarca de Porto Velho...`). Adotado o span mais curto da nova anotação.
- `relatorio`/`custas`/`honorarios`: histórica não tagueou nenhuma das três apesar de cobrir as categorias -- mas o documento tem cues reais para as três ("RELATÓRIO Dispensado.", "Isento de custas", "condeno a parte recorrente ao pagamento de honorários advocatícios... fixados em 10%"). Adotadas as tags da nova anotação, com `allowed_unmatched` declarado para `relatorio` (cláusula de dispensa, sem cue de fechamento) e `custas` (isenção declarada, sem cue de fechamento).
- `ementa_fim`: histórica tagueava um fechamento dentro do bloco final "Jurisprudência relevante citada: Não há precedentes..."; mas este documento é exatamente o formato TJRO "capa+ementa-estruturada" (Ementa: seguido direto por I-IV numeradas, sem RELATÓRIO/VOTO separado) que o guideline instrui a deixar sem par, e cita literalmente esse mesmo bloco de "Jurisprudência relevante citada" como exemplo do que NÃO fazer. Adotado `ementa_fim` sem par (`allowed_unmatched`) na nova anotação.
- `acordao_decisorio_fim`: histórica fechava depois de "À UNANIMIDADE,"; guideline descreve o fim como "'à unanimidade' / 'por maioria' + close of the collegiate result" -- a nova anotação inclui "À UNANIMIDADE" dentro do próprio fim, mais fiel à descrição. Adotado o span da nova anotação.

Independência verificada: `store.write_review` aceitou sem `NonIndependentReviewError` (famílias `prompt_subagents:haiku` vs `prompt_subagents:general-purpose`, ambas `seeded_with="none"`).
