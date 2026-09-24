---
type: AgentDecision
id: "2026-09-24-exciting-mccarthy-my6ovw-decision-reject-near-duplicate-candidates"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
question: "A live scan of data/segmenter_samples/*.jsonl (2500-18000 chars, deduped against the store's already-ingested source_uris) surfaced TJBA/574460088 (store_count=4) and, after rejecting that one, TJMA/42728925 (store_count=6) as the next unused floor-compliant candidates. Trust the live 'unused' dedup check alone (which only compares (tribunal, id) keys, not text) and proceed to annotate them, or also run a real SequenceMatcher.ratio() near-duplicate check against the whole store first, per the risk-class lesson from batch17 and batch25?"
choice: "Run the real text-similarity check before annotating either candidate, not just the (tribunal, id) dedup check. Both candidates failed it and were rejected."
rationale: "knowledge/backlog/issue-1050.md's own batch17 entry already documented TJBA/574460088 as a SequenceMatcher.ratio()=0.98 near-duplicate of TJBA/574460085 (already in the store, same court/judge/template embargos-de-declaracao ruling) -- confirmed again live this round (ratio=0.980). The backlog's own batch24 entry claims TJBA/574460088 was ingested that round, but a live check of the store (grep on source_uri, zero matches for ':574460088') shows it was never actually written -- a real inconsistency between the backlog narrative and the store's ground truth, flagged here rather than silently trusted either way. TJMA/42728925 was checked next (store_count tied lowest among remaining tribunals) and also rejected live: ratio=0.968 against TJMA/42728353, already in the store. Both rejections came from comparing candidate text against every existing document of the same tribunal with difflib.SequenceMatcher directly -- the (tribunal, id) key check alone cannot catch a genuinely new id_documento that is a boilerplate near-duplicate of a different already-ingested id, exactly the class of defect batch17/batch25 already learned to guard against. TJCE/363694252 was selected next and passed (max ratio 0.061 against the entire 191-document store)."
---

# Decisão: rejeitar candidatos quase-duplicados antes de anotar

Dois candidatos falharam a verificação real de similaridade de texto
contra o corpus inteiro (TJBA/574460088 ratio=0.98, TJMA/42728925
ratio=0.968) e foram descartados antes de qualquer anotação. Também foi
encontrada uma inconsistência real entre `knowledge/backlog/issue-1050.md`
(que afirma TJBA/574460088 foi ingerido no lote 24) e o estado real do
store (o documento nunca foi escrito) -- registrada aqui, não corrigida
silenciosamente, para uma rodada futura reconciliar a narrativa do
backlog com o estado real.
