---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-red-test-unpruned-matcher-count"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "test_red"
reference: "tests/segmenter_dataset/test_dedup.py::test_find_near_duplicates_never_builds_a_matcher_for_length_incompatible_pairs, rodado contra a implementacao original (pre-fix) de find_near_duplicates"
summary: "Teste escrito antes da correcao (TDD): monkeypatch conta quantas vezes SequenceMatcher e instanciado por find_near_duplicates sobre 16 documentos (8 curtos ~44 chars, 8 longos ~3900 chars, threshold=0.9, onde nenhum par cruzado curto/longo pode matematicamente atingir o threshold). Falhou como esperado contra a implementacao original: assert 120 <= 56 (todos os 120 pares possiveis instanciaram SequenceMatcher, incluindo os 64 pares curto/longo que sao matematicamente impossiveis de atingir o threshold -- zero poda)."
---

# Evidência: RED — nenhuma poda na implementação original

Comando: `uv run pytest -q tests/segmenter_dataset/test_dedup.py -x`

Saída relevante (contra a implementação original de
`find_near_duplicates`, antes de qualquer alteração em `dedup.py`):

```
        dedup.find_near_duplicates(records, threshold=0.9)

        total_pairs = len(records) * (len(records) - 1) // 2
        within_group_pairs = 2 * (8 * 7 // 2)
>       assert construction_count <= within_group_pairs
E       assert 120 <= 56

tests/segmenter_dataset/test_dedup.py:116: AssertionError
```

`120` é exatamente `C(16,2)` — todo par possível instanciou
`SequenceMatcher`, incluindo os `8*8=64` pares curto↔longo que o
limite matemático de comprimento prova serem inatingíveis no
`threshold=0.9` usado. Confirma ao vivo que a implementação original
não tinha nenhuma forma de poda antes de chamar o comparador caro.
