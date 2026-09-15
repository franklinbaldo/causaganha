---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-virf8r-evidence-doc3-abandoned-haiku-verbatim-failure"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "scripts/annotate_second_independent.py, doc_33709311d84406458e3e6fe26c0635d2 (não adjudicado nesta rodada)"
summary: "doc_33709311d84406458e3e6fe26c0635d2 (o acórdão longo em modelo por tópicos, 7979 chars) teve DUAS tentativas de segunda anotação nesta rodada, ambas descartadas: (1) um subagente general-purpose produziu uma anotação de alta qualidade (achou um erro real na anotação A: ementa_inicio tagueado no meio da palavra COMPLEMENTAR, dentro de uma citação de precedente do STF), mas store.write_review rejeitou com NonIndependentReviewError porque a anotação A já era model_family='prompt_subagents:general-purpose' -- mesma família, não confirmável como independente por RFC 0012 §5.3 (ver decision-family-collision-doc3); (2) uma segunda tentativa via subagente explicitamente em modelo haiku (family genuinamente distinta) falhou build_second_annotation com VerbatimFidelityError -- reconstrução com 7356 caracteres contra os 7979 do documento armazenado, indicando texto verdadeiro faltando/truncado em algum ponto, não uma leitura alternativa válida. Isso é exatamente o modo de falha de haiku em documentos longos já documentado no changelog da guideline (batch1: ~45% de taxa de falha em subagentes mais fracos). Documento abandonado para adjudicação nesta rodada -- nenhum dado corrompido foi persistido (build_second_annotation levanta antes de store.write_annotation); a anotação general-purpose original permanece na store como dado real, apenas sem review associado."
---

# Achado negativo real: doc3 abandonado após 2 tentativas

Nenhum ReviewRecord foi criado para doc_33709311d84406458e3e6fe26c0635d2 nesta rodada. Achado de processo útil para o futuro: verificar o `model_family` da anotação existente ANTES de escolher a segunda leitura (decision-family-collision-doc3), e preferir subagentes mais fortes (general-purpose) para documentos longos, já que haiku falhou fidelidade verbatim em um documento de ~8000 caracteres.
