---
type: AgentDecision
id: "2026-09-15-exciting-mccarthy-f3feqb-decision-cabecalho-inicio-narrow-anchor"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
goal_id: "2026-09-15-exciting-mccarthy-f3feqb-goal-scale-segmenter-reviews"
question: "Em doc_7e5b8558463338f1f74ee7ba8924ccfa, a anotação histórica (A) tagueou cabecalho_inicio como só 'PODER JUDICIÁRIO' (16 chars); a nova anotação independente (B, haiku) estendeu para 'PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA' (38 chars). Qual fronteira adotar?"
choice: "Adotado A (âncora curta 'PODER JUDICIÁRIO')."
rationale: "O worked example da própria guideline (Rule 6, data/segmenter_splits/annotation_guideline_v7.md linha ~95) usa exatamente '<cabecalho><inicio>PODER JUDICIÁRIO</inicio> Comarca de Porto Velho...' como âncora canônica, e essa é a convenção já usada nas 17 ReviewRecords da store (incluindo o exemplo de referência rev_64d8f456961843aa3c90ab0ab822fd1c). Estender a âncora para incluir 'DO ESTADO DE RONDÔNIA' quebraria a consistência interna do dataset sem nenhum ganho -- a guideline já resolve isso explicitamente como texto ilustrativo mínimo, não uma string livre a critério do anotador."
---

# Decisão: fronteira de cabecalho_inicio (âncora curta)

Mantida a convenção estabelecida pelo worked example da guideline e por
todas as ReviewRecords anteriores: `cabecalho_inicio` ancora só na frase
institucional mínima ("PODER JUDICIÁRIO"), não na frase completa que a
segue.
