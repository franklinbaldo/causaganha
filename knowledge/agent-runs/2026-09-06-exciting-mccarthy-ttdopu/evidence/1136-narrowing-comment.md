---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ttdopu-evidence-1136-narrowing-comment"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal_id: "2026-09-06-exciting-mccarthy-ttdopu-goal-narrow-1136-stale-scope"
kind: "issue"
reference: "https://github.com/franklinbaldo/causaganha/issues/1136#issuecomment-5556906573"
summary: "Posted a discovery comment on #1136 recording, per surface, whether the 'stale' acceptance criterion applies: yes for ProcessoLookup (snapshot generation timestamp), no for PublicationSearch (live DJEN query, no dataset timestamp in its model) and SavedConsultations (local bookmarks, no dataset), and 'different concept, already shipped' for /stats (pipeline freshness via evaluateSourceFreshness, not snapshot age). Concludes a shared cross-surface 'stale' primitive would be a wrong abstraction, and flags the only real remaining local option (deduplicating the already-duplicated stale-warning markup inside ProcessoLookup.svelte itself) as a smaller, different, optional next step rather than the assumed next #1136 slice."
---

# Evidência: comentário de descoberta na #1136

Comentário publicado registrando, superfície por superfície, se "stale" se aplica — evitando que uma rodada futura implemente incorretamente um componente genérico de "stale" entre superfícies que não compartilham o conceito.
