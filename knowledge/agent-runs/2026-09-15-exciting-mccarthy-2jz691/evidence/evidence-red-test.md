---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2jz691-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
goal_id: "2026-09-15-exciting-mccarthy-2jz691-goal-scale-segmenter-reviews"
kind: "test_red"
reference: "tests/segmenter_dataset/test_adjudicate_segmenter_review.py::test_build_review_drops_ref_normativa_before_validation"
summary: "Teste escrito ANTES do fix (TDD), reproduzindo ao vivo a falha real encontrada duas vezes nesta rodada: um resolution-file contendo <ref_normativa> (copiado de uma anotação que a guideline pede tagueada, mas que a ontologia v8 exclui) fazia build_review levantar MechanicalValidationError('category ref_normativa not in ontology') em vez de descartar a categoria como annotate_second_independent.py já faz para anotações. Rodado antes de qualquer mudança em src/segmenter_dataset/ontology.py ou scripts/adjudicate_segmenter_review.py: FAILED com exatamente esse traceback (MechanicalValidationError na linha de raise em build_review)."
---

# RED: reprodução do gap EXCLUDED_CATEGORIES em adjudicate_segmenter_review.py

`uv run pytest -q tests/segmenter_dataset/test_adjudicate_segmenter_review.py::test_build_review_drops_ref_normativa_before_validation` antes do fix: 1 failed, traceback `adjudicate_segmenter_review.MechanicalValidationError: mechanical validation failed for '...': ["category 'ref_normativa' not in ontology"]` -- reprodução exata, em miniatura, da falha ao vivo já encontrada ao adjudicar doc_f22271af e doc_bed363d9 nesta mesma rodada.
