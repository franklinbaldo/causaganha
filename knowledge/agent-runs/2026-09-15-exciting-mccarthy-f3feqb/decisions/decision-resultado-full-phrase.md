---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-f3feqb-decision-resultado-full-phrase"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal_id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
question: "Em doc_7e5b8558463338f1f74ee7ba8924ccfa, a anotação histórica (A) tagueou resultado como só o verbo 'HOMOLOGO' (8 chars); a nova anotação independente (B) tagueou a frase operativa completa 'HOMOLOGO o acordo' (17 chars). Qual fronteira adotar?"
choice: "Adotado B (frase operativa completa 'HOMOLOGO o acordo')."
rationale: "A ReviewRecord de referência já aceita na store (rev_64d8f456961843aa3c90ab0ab822fd1c) tagueia resultado como 'julgo extinto o feito' -- verbo + complemento, não o verbo isolado. A guideline (single-anchor table) descreve resultado como 'The operative verb phrase' com exemplos de frase completa ('julgo procedente', 'nego provimento', 'extingo o feito'), nunca um verbo nu. Adotar o verbo isolado de A quebraria a consistência com o precedente já estabelecido no dataset."
---

# Decisão: fronteira de resultado (frase operativa completa)

`resultado` ancora a frase operativa completa (verbo + complemento), não o
verbo isolado -- consistente com o precedente já aceito
(`rev_64d8f456961843aa3c90ab0ab822fd1c`, "julgo extinto o feito").
