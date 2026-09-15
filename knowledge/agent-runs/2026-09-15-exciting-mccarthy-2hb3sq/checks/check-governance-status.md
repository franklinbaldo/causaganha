---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-2hb3sq-check-governance-status"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
command: "uv run python scripts/segmenter_governance_status.py"
result: "observed"
evidence_id: "2026-09-15-exciting-mccarthy-2hb3sq-evidence-adjudication-decisions"
summary: "review_count e evaluation_eligible_count subiram de 29 (estado final de f0q3d4) para 31, cruzando pela primeira vez o piso combinado RFC 0012 §5.4 (>=30). document_count=61 (inalterado), annotation_count 106->108 (as 2 novas anotações Técnica 1 desta rodada), blocked_on_reviews=false. Nota: 31 é o total combinado, não a contagem por split (val/test) -- RFC 0012 §5.4 exige >=30 em CADA split."
---

# Check: status de governança do segmentador após as 2 novas reviews

```
{
  "document_count": 61,
  "annotation_count": 108,
  "review_count": 31,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 31,
  "blocked_on_reviews": false
}
```
