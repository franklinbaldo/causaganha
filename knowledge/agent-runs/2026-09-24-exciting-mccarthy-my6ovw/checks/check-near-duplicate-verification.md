---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-my6ovw-check-near-duplicate-verification"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
command: "python3 -c using difflib.SequenceMatcher(None, candidate_text, existing_doc.text).ratio() against every document already in data/segmenter (191 documents) for each candidate before annotating"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-my6ovw-evidence-batch26-ingested"
summary: "TJBA/574460088: ratio 0.980 against TJBA/574460085 (already ingested) -- REJECTED. TJMA/42728925: ratio 0.968 against TJMA/42728353 (already ingested) -- REJECTED. TJCE/363694252 (final pick): max ratio 0.061 against the whole store -- clean. TJSC/587254831 raw HTML text: max ratio 0.05 against the whole store -- clean; recomputed after HTML cleaning (2336->1037 chars): max ratio 0.118 -- still clean. Also cross-checked the two final batch candidates against each other: ratio 0.015 -- not internally duplicated."
---

# Check: verificação de near-duplicate antes de anotar
