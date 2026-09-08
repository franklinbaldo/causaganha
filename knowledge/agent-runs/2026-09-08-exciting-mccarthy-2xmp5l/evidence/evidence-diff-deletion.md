---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-2xmp5l-evidence-diff-deletion"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
goal_id: "2026-09-08-exciting-mccarthy-2xmp5l-goal-delete-tribunal-calendar"
kind: "diff"
reference: "git diff --stat HEAD -- CLAUDE.md web/src/components/TribunalCalendar.svelte"
summary: "`git rm web/src/components/TribunalCalendar.svelte` (220 lines removed, no other file touched by the deletion itself — confirmed zero references beforehand, see evidence-runtime-dead-unstyled.md). CLAUDE.md's CSS token boundary section edited: the sentence naming 'four Svelte islands' now names three (ProcessoLookup.svelte, PublicationSearch.svelte, SavedConsultations.svelte, dropping TribunalCalendar.svelte), and the 'Maintaining one of the four legacy Svelte islands' bullet now reads 'three'. `git diff --stat`: CLAUDE.md (2 lines changed), web/src/components/TribunalCalendar.svelte (220 deletions)."
---

# Evidência: diff da mudança

```
 CLAUDE.md                                  |   4 +-
 web/src/components/TribunalCalendar.svelte | 220 -----------------------------
 2 files changed, 2 insertions(+), 222 deletions(-)
```

`git rm` do componente órfão; duas linhas do CLAUDE.md corrigidas para "três ilhas legadas" em vez de "quatro".
