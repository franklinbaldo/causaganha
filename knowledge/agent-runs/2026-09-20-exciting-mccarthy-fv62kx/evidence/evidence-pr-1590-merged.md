---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-pr-1590-merged"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
goal_id: "2026-09-20-exciting-mccarthy-fv62kx-goal-djen-sample-batch24"
kind: "review"
reference: "https://github.com/franklinbaldo/causaganha/pull/1590, merge commit dba8dcf on main"
summary: "PR #1590 (batch24, #1050) merged by franklinbaldo. All 11 CI checks were green on the final head (4326a76) and all 7 Codex review threads were resolved before merge. origin/main now carries the merge commit dba8dcf; git log confirms it directly follows a90f01f (the batch23-closeout round) and c301160 (PR #1588's parser fix)."
---

# Evidência: PR #1590 mesclada

`git log origin/main --oneline` confirma:

```
dba8dcf feat(segmenter): ingest twenty-fourth real multi-tribunal batch (#1050) (#1590)
a90f01f wisk(run): close out batch23 round (PR #1586 and #1588 merged) (#1589)
c301160 fix(segmenter): recover singleton labels nested inside a pair role (#1588)
```

O merge trouxe o lote 24 líquido (5 documentos reais, após a reversão
do near-duplicate TJBA/574460088 encontrada pela revisão automatizada
do Codex) para `main`. Branch local `claude/exciting-mccarthy-fv62kx`
reiniciada a partir de `origin/main` para este commit de fechamento,
seguindo a convenção já estabelecida pelas rodadas anteriores desta
linhagem (batch22/#1587, batch23/#1589) de um commit de fechamento
separado após a confirmação do merge.
