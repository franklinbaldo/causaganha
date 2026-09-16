---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-c4y4rc-evidence-real-store-ceiling"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-per-split-floor-ceiling-2026-09-16.json"
summary: "uv run python scripts/segmenter_governance_status.py contra o store real (data/segmenter, 61 documentos, 31 adjudicados) mostra val_count=test_count=9 E val_ceiling_at_full_adjudication=test_ceiling_at_full_adjudication=9 -- ou seja, mesmo simulando adjudicacao de 100% do corpus atual, o teto continua em 9/9, bem abaixo do piso de RFC 0012 Sec 5 item 4 (>=30 cada). corpus_scale_blocks_floor=true confirma que o gargalo real e o tamanho do corpus (#1050), nao a cobertura de adjudicacao (#1051)."
---

# Evidencia: teto estrutural confirmado no store real

```json
{
  "document_count": 61,
  "annotation_count": 108,
  "review_count": 31,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 31,
  "blocked_on_reviews": false,
  "val_count": 9,
  "test_count": 9,
  "val_ceiling_at_full_adjudication": 9,
  "test_ceiling_at_full_adjudication": 9,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": true
}

WARNING: RFC 0012 Sec 5 item 4's per-split floor (>= 30 val, >= 30 test,
each adjudicated) cannot be reached with the current corpus size (61
documents), even at 100% adjudication: val_ceiling=9, test_ceiling=9.
Adjudicating more of the existing pool (#1051) cannot cross this ceiling
-- growing the total corpus is required (#1050).
```

Comando: `uv run python scripts/segmenter_governance_status.py` (default
`--store data/segmenter`), executado contra o HEAD real desta rodada
(61 documentos, 108 anotacoes, 31 reviews aceitos -- estado deixado pela
rodada anterior mesclada, 2hb3sq/PR #1533).
