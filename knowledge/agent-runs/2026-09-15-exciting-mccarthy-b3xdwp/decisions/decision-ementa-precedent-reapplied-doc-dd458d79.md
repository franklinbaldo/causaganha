---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-b3xdwp-decision-ementa-precedent-reapplied-doc-dd458d79"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
question: "doc_dd458d79ebdf7c65daf39d1a51cf1ea9 é outro export capa+ementa-estruturada do TJRO (Ementa: seguida de I. CASO EM EXAME/II. QUESTÕES EM DISCUSSÃO/III. RAZÕES DE DECIDIR/IV. DISPOSITIVO E TESE), sem RELATÓRIO nem VOTO separados. A anotação histórica (haiku) fechou ementa_fim dentro da seção final 'Jurisprudência relevante citada' (~2500 caracteres depois do início da ementa); o subagente independente desta rodada deixou ementa não-casada (estende até EOD). Aplica-se o mesmo precedente de 2cjjig (decision-ementa-extends-to-eod-consistency)?"
choice: "Sim. Reaplicado o mesmo precedente: ementa fica não-casada (estende até EOD) neste documento também, rejeitando o fechamento tardio da anotação histórica."
rationale: "2cjjig já estabeleceu, para exatamente este formato estrutural (capa+ementa-estruturada, sem relatório/voto), que nenhum cue de fechamento real existe no texto -- então fechar ementa em qualquer ponto arbitrário do documento é fabricar um cue que a guideline explicitamente proíbe ('don't fabricate a closing tag'). O fechamento da anotação histórica aqui (dentro de 'Jurisprudência relevante citada', a mais de 2500 caracteres da abertura) é ainda mais artificial que o disagreement original de 2cjjig, reforçando que a leitura correta para todo este formato de export é a mesma independentemente do documento específico. Também reconfirma a leitura de ementa_inicio como o cue literal 'Ementa:' (não o primeiro conteúdo substantivo), pelo mesmo motivo já registrado em 2cjjig."
---

# Decisão: reaplicar o precedente de fronteira de ementa (rodada b3xdwp)

Terceira ocorrência do mesmo padrão estrutural (após os dois documentos de
2cjjig): exports capa+ementa-estruturada do TJRO sem relatório/voto não têm
cue de fechamento real para `ementa_fim`, então a leitura correta é sempre
não-casada (estende até EOD), nunca um fechamento fabricado em outro ponto
do texto. Como o próprio next_move de 2cjjig já antecipou, esta é a
terceira ocorrência do disagreement -- vale registrar esta leitura na
CHANGELOG da annotation_guideline_v7.md numa rodada futura, em vez de
repetir a decisão de adjudicação a cada vez.
