---
type: AgentDecision
id: "2026-09-26-exciting-mccarthy-ku8qje-decision-update-stale-guard"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
question: "Apos o Lote 28, `tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_has_at_least_one_evaluation_eligible_document` passou a falhar (`assert status['corpus_scale_blocks_floor'] is True` -- agora `False`). Tratar isso como uma regressao a investigar, ou atualizar o teste?"
choice: "Atualizar o teste: trocar `corpus_scale_blocks_floor is True` por `is False`, adicionar `val_ceiling_at_full_adjudication`/`test_ceiling_at_full_adjudication >= 30`, e manter `meets_rfc_0012_split_floor is False` (ainda verdadeiro -- falta cobertura de adjudicacao, nao mais escala de corpus)."
rationale: "O proprio docstring/comentario do teste, escrito quando o guard foi introduzido, ja previa exatamente este momento: 'If this assertion ever starts failing because corpus_scale_blocks_floor is False, issue #1050 (corpus scale-up) has made enough real progress to lift this structural ceiling -- update/remove this guard instead of treating a flip here as a failure.' `scripts/segmenter_governance_status.py` confirma ao vivo que o teto real de val/test agora e 30/30 (nao mais 29/29), exatamente a condicao que o comentario original descreve como sucesso, nao como bug. Tratar essa mudanca como uma falha a corrigir no codigo de producao seria o oposto do que o proprio teste pede -- e exatamente o padrao ja seguido por um guard irmao no mesmo arquivo (`test_real_store_has_at_least_one_evaluation_eligible_document` em si, cujo proprio docstring documenta ter sido atualizado da mesma forma quando #1051 produziu o primeiro ReviewRecord real)."
---

# Decisão: atualizar o guard de teto de corpus, não tratar como regressão

O teste `corpus_scale_blocks_floor is True` foi escrito com um comentário
explícito prevendo este exato momento ("update/remove this guard instead
of treating a flip here as a failure"). O Lote 28 elevou o teto real de
val/test para 30/30 pela primeira vez -- atualizado o teste para refletir
esse marco real, não revertido o trabalho para forçar o teste antigo a
passar.
