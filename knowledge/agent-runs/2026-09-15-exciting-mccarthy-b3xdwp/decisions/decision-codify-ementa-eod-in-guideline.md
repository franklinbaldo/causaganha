---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-b3xdwp-decision-codify-ementa-eod-in-guideline"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
question: "2cjjig já havia deixado como next_move explícito: 'vale registrar a leitura estende até EOD para exports sem relatório/voto na própria annotation_guideline_v7.md (CHANGELOG) em vez de repetir a decisão de adjudicação a cada rodada'. Com esta rodada, o mesmo disagreement de ementa_fim ocorreu pela terceira vez (2 documentos em 2cjjig, 1 em b3xdwp) -- deve a leitura ser codificada na guideline agora, em vez de re-adjudicada informalmente de novo na próxima rodada?"
choice: "Sim. Editada a linha `ementa` da tabela de start/end pairs em data/segmenter_splits/annotation_guideline_v7.md para declarar explicitamente a leitura 'estende até EOD' para exports capa+ementa-estruturada do TJRO, e adicionada a entrada v7.4 em annotation_guideline_v7_CHANGELOG.md documentando a motivação (3 ocorrências reais do mesmo disagreement) e confirmando que não há mudança de ontology_version nem invalidação de anotações anteriores -- é mudança só de guideline, mesma categoria das entradas v7.1/v7.2/v7.3 já registradas."
rationale: "RFC 0012 §5 point 1's última bullet permite mudanças só-de-guideline sem bump de ontology_version; as três entradas anteriores da própria CHANGELOG (v7.1-v7.3) seguem exatamente esse padrão para gaps descobertos em produção real. Codificar a leitura agora, em vez de deixar como 'next_move para a próxima rodada' pela segunda vez, reduz o custo de adjudicação de rodadas futuras sobre este mesmo formato de documento (não é hipotético -- já ocorreu 3 vezes hoje) e está dentro da autorização explícita desta rodada de melhorar specs/schemas quando isso melhora a arquitetura. Nenhum teste referencia o conteúdo literal do arquivo da guideline (confirmado via grep em tests/), então a edição não quebra nenhuma suíte."
---

# Decisão: codificar a leitura de `ementa_fim` na guideline (v7.4)

Terceira ocorrência do mesmo disagreement em um único dia de rodadas
justificou parar de re-adjudicar informalmente e escrever a regra
diretamente na guideline (`ementa` row + CHANGELOG v7.4), seguindo o
padrão já estabelecido pelas entradas v7.1-v7.3 para gaps descobertos em
produção real.
