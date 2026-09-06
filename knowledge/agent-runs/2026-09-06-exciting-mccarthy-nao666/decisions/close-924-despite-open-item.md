---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-nao666-decision-close-924-despite-open-item"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
question: "Issue #924 has one sub-item (§3.2, segmenter double-annotation) that live-checking confirms is still genuinely incomplete. Should the issue stay open until §3.2 is done, or close now?"
choice: "Close #924 now as completed, with the comment explicitly naming §3.2 as the one open item and pointing to #1047 (the segmenter's own evidence-first roadmap issue) as where it is already tracked."
rationale: "#924 is not a feature request or a bug report with a single acceptance criterion — its own body frames it as a one-shot, unverified model review whose job is to surface candidate work ('o que sobreviver à verificação merece issue própria; esta aqui é o ponto de partida, não o registro final'), not to serve as a standing tracker. §3.2 already has better-scoped, purpose-built tracking: #1047 is the segmenter's dedicated evidence-first roadmap issue, with #1050-1057 breaking the annotation/training path into concrete steps. Keeping #924 open only to duplicate that tracking would mean two issues (#924 and #1047) both needing to be re-read every round to determine whether segmenter annotation has progressed, which is exactly the kind of stale-issue re-verification cost this round is trying to eliminate. Closing #924 with an explicit pointer to #1047 for the one real remaining item is more accurate than leaving a five-sub-item review issue open for a single line that belongs elsewhere."
---

# Decisão: fechar a #924 mesmo com um item pendente

O item pendente (§3.2) já tem dono próprio (#1047). Manter a #924 aberta só para isso duplicaria rastreamento e forçaria rodadas futuras a reler um documento de triagem já esgotado. Fecha-se com apontamento explícito.
