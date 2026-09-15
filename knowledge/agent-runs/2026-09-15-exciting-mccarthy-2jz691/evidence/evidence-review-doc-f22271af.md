---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-review-doc-f22271af"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_f22271af51fd1d9e2e0f296aea1b9617/rev_7176441ce667d91a35fb6b19c152442b.xml"
summary: "Décimo ReviewRecord real da store (review_count 9->10). Este documento já tinha uma segunda anotação seeded (agent_repair:semantic_audit_2026_09, seeded_with=semantic_audit_missing_anchor_repair) que NÃO conta para independência (RFC 0012 §5.3) -- a subagente Técnica 1 isolada desta rodada produziu a primeira segunda anotação genuinamente independente (ann_5ce1823ce5ddce4fa427419d369a86e7, seeded_with=none, par válido com a histórica). Disagreement real: (1) dispositivo_abertura -- histórico marcou 'HOMOLOGO O ACORDO' (mesmo padrão de doc_bef14659), subagente marcou 'Isso posto', variante estilística EXATA do exemplo canônico 'Posto isso' da guideline, imediatamente antes de 'julgo extinto o feito'; adotado o do subagente. (2) fundamentacao_legal -- histórico tagueou só 1 citação, subagente tagueou 5 distintas (guideline exige every distinct citation); adotado o conjunto completo do subagente. (3) 3 spans ref_normativa do subagente removidos manualmente do resolution-file por serem categoria excluída da ontologia v8 -- MESMO gap que motivou decision-fix-excluded-categories-gap desta rodada (a segunda ocorrência ao vivo do mesmo problema, depois corrigido estruturalmente). (4) custas_inicio estendido para 'Sem custas finais' (histórico) em vez de 'Sem custas' truncado (subagente). (5) honorarios_fim ajustado para a frase completa 'nos termos do acordo.' (histórico) em vez da palavra isolada e ambígua 'acordo' (subagente, que recorre dezenas de vezes no documento). cabecalho, ref_processual, resultado, encerramento coincidiram e foram mantidos."
---

# Review real #10: doc_f22271af51fd1d9e2e0f296aea1b9617

`uv run python scripts/segmenter_governance_status.py` antes: review_count=9. Depois: review_count=10, evaluation_eligible_count=10 -- meta mínima do success_signal desta rodada (>=10) atingida.
