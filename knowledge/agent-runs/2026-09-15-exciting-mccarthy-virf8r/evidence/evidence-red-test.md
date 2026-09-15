---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-virf8r-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
goal_id: "2026-09-15-exciting-mccarthy-virf8r-goal-scale-segmenter-reviews"
kind: "test_red"
reference: "tests/segmenter_dataset/test_adjudicate_segmenter_review.py::test_main_passes_allowed_unmatched_through_cli"
summary: "Ao tentar adjudicar o doc_0bb1cdf4d3ce8cb2400765e788c767e4 (um acórdão em modelo por tópicos sem cue de fechamento de ementa), scripts/adjudicate_segmenter_review.py falhou com MechanicalValidationError mesmo com uma resolução legitimamente unmatched, porque a CLI não expunha --allowed-unmatched (só build_review, a função pura, aceitava o parâmetro). RED: novo teste chamando _MODULE.main(argv) com --allowed-unmatched falhou com 'unrecognized arguments' (SystemExit 2) antes da correção."
---

# RED: CLI sem --allowed-unmatched

`uv run pytest tests/segmenter_dataset/test_adjudicate_segmenter_review.py::test_main_passes_allowed_unmatched_through_cli -q` -- `argparse.ArgumentParser` rejeitava `--allowed-unmatched` como argumento desconhecido antes da correção, confirmando que o parâmetro só existia na função pura `build_review`, não na CLI que a chama.
