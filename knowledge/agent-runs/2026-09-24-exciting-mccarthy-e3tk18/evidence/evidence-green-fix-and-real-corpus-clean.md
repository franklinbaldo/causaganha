---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal_id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
kind: "test_green"
reference: "scripts/segmenter_semantic_audit.py; tests/segmenter_dataset/test_segmenter_audit_scripts.py"
summary: "Correcao: as duas checagens de substring exata ('<ref_normativa>' in xml_text / '<fundamentacao_legal>' in xml_text) e os dois regex de extracao de span (r'<ref_normativa>(.*?)</ref_normativa>' / r'<fundamentacao_legal>(.*?)</fundamentacao_legal>') foram trocados por versoes que aceitam atributos (re.search(r'<ref_normativa\\b', ...) e r'<ref_normativa\\b[^>]*>(.*?)</ref_normativa>', idem para fundamentacao_legal). Apos a correcao: os 4 novos testes sinteticos (operative_on_reasoning_or_verb, capitulo_merito_on_prose, ref_processual_mismatch, ref_normativa_overlap) e o novo teste de regressao contra o corpus real ficam GREEN -- 11/11 em tests/segmenter_dataset/test_segmenter_audit_scripts.py. Rerodar find_anti_patterns() contra data/segmenter (corpus real, 193 documentos/250 anotacoes) apos a correcao mostra exatamente os mesmos 7 achados collapsed ja conhecidos e catalogados (5x fundamentacao_legal_collapsed, 2x valor_condenacao_collapsed) e zero achados novos dos 4 tipos anteriormente sem cobertura -- a correcao fecha uma lacuna real de deteccao sem revelar nenhum defeito semantico escondido no corpus atual."
---

# Evidencia: GREEN apos a correcao, corpus real confirmado limpo

```
$ uv run pytest -q tests/segmenter_dataset/test_segmenter_audit_scripts.py -v
...
11 passed in 0.35s
```

```
$ uv run python -c "
from pathlib import Path
from scripts.segmenter_semantic_audit import find_anti_patterns
findings = find_anti_patterns(Path('data/segmenter'))
from collections import Counter
c = Counter()
for doc_id, fs in findings.items():
    for f in fs:
        c[f['type']] += 1
print(c)
"
Counter({'fundamentacao_legal_collapsed': 5, 'valor_condenacao_collapsed': 2})
```

Identico ao estado pre-existente documentado por rodadas anteriores
(mesma allowlist de 7 documentos de
`test_real_store_has_at_most_the_one_known_collapsed_false_positive`).
`scripts/segmenter_governance_status.py` reconfirmado ao vivo:
`document_count=193`, `annotation_count=250` -- inalterados (este e um
fix de ferramenta de auditoria, nao um lote de ingestao de dados).
