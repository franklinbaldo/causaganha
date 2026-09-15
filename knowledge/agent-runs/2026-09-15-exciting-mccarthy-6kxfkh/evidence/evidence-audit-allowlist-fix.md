---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6kxfkh-evidence-audit-allowlist-fix"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
goal_id: "2026-09-15-exciting-mccarthy-6kxfkh-goal-scale-segmenter-reviews"
kind: "test_green"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive"
summary: "RED: apos ingerir a nova anotacao de doc_3cffd7961e9fc910f6ae628f5aaa6c40, o teste de allowlist falhou (collapsed_doc_ids ganhou um segundo membro). GREEN: causa raiz investigada e documentada -- ref_normativa e excluida do espaco trainable (RFC 0012 Sec 5, ontology.EXCLUDED_CATEGORIES) e por isso nunca chega a annotation record que o heuristico varre, entao o heuristico >3 'art.' conta citacoes de uma lista bibliografica ('Dispositivos relevantes citados') que sao corretamente ref_normativa, nao fundamentacao_legal. Allowlist estendida com razao documentada, seguindo o precedente ja escrito no proprio teste (doc_d61aecbf...) em vez de silenciar o assert."
---

# Evidencia: RED -> GREEN no teste de allowlist da auditoria semantica

RED (antes da correcao):

```
FAILED tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive
AssertionError: assert {'doc_3cffd79...8f655285fe6c'} == {'doc_d61aecb...8f655285fe6c'}
Extra items in the left set: 'doc_3cffd7961e9fc910f6ae628f5aaa6c40'
```

Investigacao: `scripts/segmenter_semantic_audit.py`'s
`fundamentacao_legal_collapsed` dispara quando um documento tem exatamente
1 tag `fundamentacao_legal` mas `text.lower().count("art.") +
count("artigo") > 3`. A anotacao adjudicada de doc_3cffd tem 1
`fundamentacao_legal` real (CDC art. 42, a reasoning phrase da secao III.
RAZÕES DE DECIDIR) e nenhum `ref_normativa` -- nao porque foram omitidos,
mas porque `build_second_annotation` chama `drop_excluded_categories`
antes de persistir, e `ref_normativa` esta em `EXCLUDED_CATEGORIES` desde
a decisao do RFC 0012 Sec 5 (nao faz parte do espaco trainable). A secao
"IV. DISPOSITIVO E TESE" deste documento tem uma lista bibliografica
("Dispositivos relevantes citados: CF/1988 art. 5º; CDC art. 42; CPC art.
373; CC arts. 398 e 406; ... jurisprudencia ...") com 5+ ocorrencias de
"art."/"artigo" que sao citacoes puras (ref_normativa), nao reasoning
phrases -- exatamente o caso que o heuristico nao consegue distinguir.

GREEN: allowlist de
`test_real_store_has_at_most_the_one_known_collapsed_false_positive`
estendida para `{"doc_d61aecbf08b525a26f908f655285fe6c",
"doc_3cffd7961e9fc910f6ae628f5aaa6c40"}`, com o docstring do teste
atualizado explicando a nova entrada e a razao (mesmo padrao ja
estabelecido pelo teste para o primeiro caso, nunca silenciando o assert).

```
uv run pytest tests/segmenter_dataset -q
377 passed
```
