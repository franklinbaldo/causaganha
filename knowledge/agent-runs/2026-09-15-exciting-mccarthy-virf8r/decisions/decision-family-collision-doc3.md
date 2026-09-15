---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-virf8r-decision-family-collision-doc3"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
question: "doc_33709311d84406458e3e6fe26c0635d2's existing annotation já tinha model_family='prompt_subagents:general-purpose' -- a mesma família declarada para a segunda anotação produzida nesta rodada por um subagente general-purpose. store.write_review corretamente rejeitou o par com NonIndependentReviewError (RFC 0012 §5.3: mesma família não é independência confirmável). Abandonar este documento, forçar um rótulo de família diferente sem justificativa real, ou produzir uma terceira anotação genuinamente de outra família?"
choice: "Produzir uma nova segunda anotação para o mesmo documento via um subagente rodando explicitamente no modelo haiku (model_family='prompt_subagents:haiku'), reaproveitando toda a leitura/diff já feita, e adjudicar o par ORIGINAL vs HAIKU em vez de ORIGINAL vs GENERAL-PURPOSE. A anotação general-purpose já escrita fica na store como dado real (não é descartada), apenas não participa deste review."
rationale: "Rotular artificialmente a segunda anotação com uma família diferente da que realmente a gerou seria uma corrupção de proveniência -- exatamente o tipo de atalho que a guarda de independência do RFC 0012 existe para impedir (correlação de erros de um mesmo modelo/família contando como duas leituras independentes). Abandonar o documento descartaria uma investigação real e já valiosa (encontrou um erro genuíno na anotação A: ementa_inicio tagueado no meio da palavra COMPLEMENTAR, dentro de uma citação de precedente do STF). Rodar um subagente explicitamente em outro modelo (haiku) é uma segunda leitura genuinamente de outra família, sem gambiarra no rótulo -- e vira um achado de processo relevante para rodadas futuras: verificar o model_family da anotação existente ANTES de escolher qual família usar na segunda leitura, evitando este retrabalho."
---

# Decisão: colisão de família em doc3, resolvida com uma segunda leitura de outra família real

Achado de processo registrado para rodadas futuras: ao escolher um documento candidato do pool de 43, checar o `model_family` da anotação existente primeiro, e escolher deliberadamente um subagente de família diferente (ex.: `model: "haiku"` no Agent tool) quando a existente já for `prompt_subagents:general-purpose`.
