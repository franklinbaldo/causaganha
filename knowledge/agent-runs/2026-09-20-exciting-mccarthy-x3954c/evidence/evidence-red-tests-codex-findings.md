---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-red-tests-codex-findings"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "test_red"
reference: "tests/segmenter_dataset/test_dedup.py::test_find_near_duplicates_threshold_zero_matches_every_pair, ::test_find_near_duplicates_matches_two_empty_texts, ::test_find_near_duplicates_keeps_exact_threshold_boundary_despite_float_rounding, ::test_find_near_duplicates_preserves_brute_force_order_for_equal_ratio_pairs -- rodados contra a implementacao da poda antes da correcao dos achados do Codex"
summary: "4 testes escritos para reproduzir os 3 achados do Codex (2 achados P2 duplicados sobre o mesmo bug de length_a==0/threshold<=0, 1 P1 de arredondamento de ponto flutuante na fronteira exata do threshold, 1 P2 de ordem de pares empatados). Todos os 4 falharam contra a implementacao anterior, confirmando que os achados eram reais: threshold=0 retornava [] em vez de todos os pares; duas strings vazias nao eram reportadas como near-duplicate; 'aa'/'aaa' em threshold=0.8 (ratio real exato 0.8) nao era reportado; a ordem de dois pares empatados (0.5) divergia da implementacao de referencia brute-force."
---

# Evidência: RED — os 3 achados do Codex reproduzidos

```
$ uv run pytest -q tests/segmenter_dataset/test_dedup.py -k "threshold_zero or two_empty_texts or exact_threshold_boundary or preserves_brute_force_order"
FFFF
FAILED ...::test_find_near_duplicates_threshold_zero_matches_every_pair
  assert [] == [('a', 'b', 0.35...), ('a', 'c', 0.0), ('b', 'c', 0.0)]
FAILED ...::test_find_near_duplicates_matches_two_empty_texts
  assert [] == [('a', 'b', 1.0)]
FAILED ...::test_find_near_duplicates_keeps_exact_threshold_boundary_despite_float_rounding
  assert [] == [('a', 'b', 0.8)]
FAILED ...::test_find_near_duplicates_preserves_brute_force_order_for_equal_ratio_pairs
  assert [('1', '2', 0.5), ('0', '2', 0.5)] == [('0', '2', 0.5), ('1', '2', 0.5)]
```

Confirma ao vivo, com um teste por achado, que nenhum dos 3 comentários
de review do Codex era ruído: cada um aponta um caso real onde a
implementação da poda (antes desta correção) divergia do contrato
anterior da função ou da equivalência com um scan de referência.
