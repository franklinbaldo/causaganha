---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-b3xdwp-evidence-doc-dd458d79-zero-tag-attempt"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
goal_id: "2026-09-15-exciting-mccarthy-b3xdwp-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "subagente Técnica 1 isolado, agentId a16ff57835fd2584f (interno)"
summary: "Primeira tentativa de segunda anotação independente para doc_dd458d79ebdf7c65daf39d1a51cf1ea9 falhou: o subagente retornou o texto do documento integralmente sem nenhuma tag XML, apesar do prompt canônico incluir os checkpoints explícitos desenhados exatamente para prevenir essa falha (RFC 0012 §9's changelog, batch1 ~45% zero-tag failure rate). Descartada sem ingestão -- não consumiu quota de anotação real na store (nenhum AnnotationRecord foi escrito). Uma segunda tentativa (com prompt reforçado, explicitamente citando esta falha e proibindo zero tags para um documento normal de uma página) foi dispatchada em seguida e produziu uma anotação válida (ver evidence-review-doc-dd458d79), ingerida e adjudicada."
---

# Evidência: tentativa descartada (zero tags) para doc_dd458d79

Mesmo padrão de falha já documentado no changelog do RFC 0012 §9 e em
rodadas anteriores (virf8r, doc3 abandonado por falha de verbatim): quando
um subagente falha em produzir tags, a resposta correta é descartar a
tentativa sem ingerir (nenhum AnnotationRecord inválido chega à store) e
tentar de novo com reforço explícito, não forçar uma anotação vazia como
se fosse um resultado válido.
