---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-zrek2s-evidence-collapsed-false-positive-verified"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
kind: "test_green"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_real_store_has_at_most_the_one_known_collapsed_false_positive"
summary: "scripts/segmenter_semantic_audit.py sinalizou doc_2a07306d88d1acebcdc0aff9958f7009 (TJRR, lote 7) como valor_condenacao_collapsed (R$ aparece 5x, so 1 valor_condenacao marcado). Verificado contra o texto-fonte: as 5 ocorrencias de R$ sao o mesmo valor de restituicao (R$ 843,47) repetido no relatorio/fundamentacao antes da tag operativa no dispositivo -- falso positivo genuino, mesmo formato do achado ja documentado para doc_d61aecbf08b525a26f908f655285fe6c. Allowlist do teste estendida com a verificacao e o raciocinio documentados, sem silenciar o assert."
---

# Evidencia: falso positivo do audit semantico verificado contra o texto-fonte

## Achado

```
uv run python -c "... find_anti_patterns(Path('data/segmenter')) ..."
doc_2a07306d88d1acebcdc0aff9958f7009 {'type': 'valor_condenacao_collapsed',
  'reason': "only 1 valor_condenacao tagged, but 'R$' appears >2 times"}
```

## Verificacao contra o texto-fonte (nao apenas confiar no achado do subagente)

```
'Valor da Causa: : R$2.450,30'                                    -- valor da causa, nao condenacao
'no valor de R$ 843,47. Ao final, pleiteia...'                    -- pedido, no relatorio
'no valor de R$ 843,47. Sobre o tema, o STJ...'                   -- mesmo valor, na fundamentacao
'valor de R$\n843,47 ao orgao de transito...'                     -- mesmo valor, ainda na fundamentacao
'<valor_condenacao>R$ 843,47</valor_condenacao>'                  -- tag correta, unica, no dispositivo
```

Confirma: 1 valor de condenacao real (R$ 843,47), citado 4 vezes antes
da tag operativa por ser o proprio objeto do litigio (tarifa contestada)
narrado no relatorio e na fundamentacao. A tag unica esta correta; a
heuristica `>2` do audit e o falso positivo, no mesmo formato ja
documentado para `doc_d61aecbf08b525a26f908f655285fe6c` (rodada
anterior).

## Acao

Estendida a allowlist de `test_real_store_has_at_most_the_one_known_collapsed_false_positive`
com `doc_2a07306d88d1acebcdc0aff9958f7009` e o raciocinio acima no
docstring do teste -- nunca silenciando o assert, seguindo a propria
instrucao do teste.

```
uv run pytest tests/segmenter_dataset/test_segmenter_audit_scripts.py -q
..............                                                           [100%]
```
