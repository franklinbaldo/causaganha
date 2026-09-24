---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-my6ovw-decision-relax-length-floor-for-tjsc"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
question: "batch5 established an informal ~2500-char candidate-length floor to avoid trivial/malformed excerpts. TJSC (the single most under-represented tribunal in the store, count=1) has zero remaining unused Sentenca/Acordao candidates at or above that floor -- only two shorter acordaos (2336 and 2459 chars). Skip TJSC this batch and pick a second floor-compliant candidate from an already-better-represented tribunal instead, or relax the floor for TJSC specifically?"
choice: "Relax the floor for TJSC/587254831 (2336 chars, Acordao) this batch."
rationale: "The 2500-char floor was never a validate_record() rule -- it is an empirical selection heuristic from batch5's own narrative, adopted to avoid documents too thin to carry real anchors. #1050's explicit ask is 'multiple tribunals/sources', and TJSC sitting at store_count=1 for 26 batches is the more direct violation of that goal than a merely-below-heuristic-floor document length. The prompt's own self-check for a document this short only requires 'aim to tag every genuine anchor... re-read if fewer than ~5', not a hard tag-count floor (that floor is stated for documents >3000 chars). Choosing a second TJBA-adjacent tribunal instead would have grown an already-4-strong tribunal at the direct cost of leaving the weakest tribunal in the whole corpus untouched for a 27th consecutive batch -- a worse trade for #1050's stated intent than annotating a slightly shorter but genuine, well-formed acordao."
---

# Decisão: relaxar o piso de comprimento para TJSC
