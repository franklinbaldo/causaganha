---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-uyx7xc-decision-predecode-html-entities"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
question: "The previous round's next_move offered two options for candidates whose texto_limpo contains literal HTML entities (e.g. TJGO/TJTO): pre-decode with html.unescape() before building candidates.json, or give the annotation prompt an explicit worked example for escaping a literal source '&' without decoding. Which should this round use?"
choice: "Pre-decode every selected candidate's texto_limpo with html.unescape() before writing candidates.json and the per-document text file handed to each subagent, uniformly across all 7 candidates (not just the ones visibly affected)."
rationale: "html.unescape() is idempotent on text with no entities (verified live: 0 entities found in TRF2/TST/TJPI picks, so decoding them is a no-op), and it fully removed every '&[a-zA-Z]+;' occurrence found in the affected picks (TJGO 394, TJMG 321, TJRS 118, TJTO 513) without any manual prompt engineering or extra subagent instruction to get right. The prompt-escaping alternative would add a new failure mode (a subagent misjudging when to apply it) for no benefit, since the source texts here are stored/transmitted values, not something the guideline needs a human/agent to distinguish 'real ampersand' from 'decode error' -- decoding once, mechanically, before the subagent ever sees the text is strictly simpler and was validated end-to-end this round, including on the exact TJTO document (id=285645419) batch2 previously discarded for this reason."
---

# Decisao: pre-decodificar entidades HTML antes de montar candidates.json

`html.unescape()` aplicado uniformemente a todos os 7 candidatos, nao so
aos afetados -- e idempotente para texto sem entidades e resolveu 100% das
ocorrencias encontradas nos afetados (ate 513 num unico documento),
incluindo o mesmo documento TJTO descartado na rodada anterior.
