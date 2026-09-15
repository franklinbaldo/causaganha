---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-review-doc-bef14659"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "runtime"
reference: "data/segmenter/reviews/doc_bef14659dbd6e104f31ccd36359e38b8/rev_7225dade8a19095a5d541e468957747c.xml"
summary: "Nono ReviewRecord real da store (review_count 8->9). Subagente Técnica 1 isolado (sem visibilidade da anotação histórica) produziu ann_6227dea2c69822633747d82505546969 (model_family=prompt_subagents:general-purpose, seeded_with=none -- par independente com a anotação histórica model_family=historical_migration_unspecified). Disagreement real: (1) dispositivo_abertura -- histórico marcou 'Homologo o acordo' (ato substantivo anterior), o subagente marcou 'em consequência' (conectora formulaica imediatamente antes de 'JULGO EXTINTO', o resultado real -- Rule 2 da guideline); adotado o do subagente por ser estruturalmente mais fiel à definição de dispositivo_abertura. (2) custas/honorarios -- o subagente OMITIU as duas regiões inteiras (falso negativo claro: o texto discute explicitamente 'condeno ... ao pagamento das custas finais' e 'honorários periciais remanescentes'); mantidas as duas do histórico. (3) cabecalho_fim -- histórico fechou em 'JAQUELINE FERNANDES SILVA, OAB nº RO8128' (nome completo + OAB), subagente fechou apenas em 'OAB nº RO8128' (fragmento); adotado o histórico por ser mais fiel ao 'last party/OAB' da guideline. Demais spans (cabecalho_inicio, ref_processual, fundamentacao_legal x2, resultado, encerramento) coincidiram exatamente e foram mantidos sem alteração."
---

# Review real #9: doc_bef14659dbd6e104f31ccd36359e38b8

`uv run python scripts/segmenter_governance_status.py` antes: review_count=8. Depois: review_count=9, evaluation_eligible_count=9.
