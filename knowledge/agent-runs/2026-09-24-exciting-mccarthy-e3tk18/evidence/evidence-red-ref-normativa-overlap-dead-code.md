---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-red-ref-normativa-overlap-dead-code"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal_id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_find_anti_patterns_detects_ref_normativa_overlap"
summary: "Novo teste sintetico, escrito antes da correcao, constroi uma fixture com um label fundamentacao_legal envolvendo (nesting) um label ref_normativa e afirma que find_anti_patterns() detecta um finding ref_normativa_overlap. Rodado antes da correcao do regex: FAILED com 'assert False' -- confirmando ao vivo que a checagem original (substring exata '<ref_normativa>'/'<fundamentacao_legal>' sem atributos) nunca dispara, porque o XML real serializado pela store sempre inclui o atributo ord=\"N\" em cada label (<ref_normativa ord=\"1\">...</ref_normativa>), nunca a forma sem atributo. Confirmado tambem programaticamente contra data/segmenter/annotations/ inteiro: grep por '<ref_normativa>' e '<fundamentacao_legal>' (sem atributos) retorna 0 arquivos em todo o corpus real."
---

# Evidencia: teste RED confirma detector morto

```
$ git stash push -- scripts/segmenter_semantic_audit.py   # reverte so o fix, mantem o teste novo
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_audit_scripts.py -k "detects_ref_normativa_overlap or detects_operative or detects_capitulo or detects_ref_processual"
...
>       assert any(f["type"] == "ref_normativa_overlap" for f in findings[doc.document_id])
E       assert False
E        +  where False = any(<generator object ...>)
FAILED tests/segmenter_dataset/test_segmenter_audit_scripts.py::test_find_anti_patterns_detects_ref_normativa_overlap
$ git stash pop   # reaplica o fix
```

Os outros 3 testes sinteticos novos (operative_on_reasoning_or_verb,
capitulo_merito_on_prose, ref_processual_mismatch) passaram nessa
mesma rodada sem o fix -- confirmando que so `ref_normativa_overlap`
estava quebrado, nao os outros 3 tipos previamente sem cobertura.

Confirmacao independente contra o corpus real (antes de qualquer
mudanca de codigo):

```
$ grep -rl "<ref_normativa>" data/segmenter/annotations/ | wc -l
0
$ grep -rl "<fundamentacao_legal>" data/segmenter/annotations/ | wc -l
0
$ grep -rl "<fundamentacao_legal ord=" data/segmenter/annotations/ | wc -l
# (arquivos reais, forma sempre com atributo)
```
