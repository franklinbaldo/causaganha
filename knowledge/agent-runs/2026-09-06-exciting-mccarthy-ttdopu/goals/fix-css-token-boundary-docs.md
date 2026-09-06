---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-ttdopu-goal-fix-css-token-boundary-docs"
run_id: "2026-09-06-exciting-mccarthy-ttdopu"
goal: "Rewrite CLAUDE.md's '### CSS token boundary' section to describe the site's actual current CSS architecture (a single Panda CSS design system via the `cobogo` preset, with a small legacy compatibility shim for four not-yet-converted Svelte islands) instead of the retired 'Brazilian Modernism vs. Semantic, split by page type' model."
rationale: "This exact staleness has been independently rediscovered and flagged by four prior rounds (6tcxrn, an earlier round, nao666, s5c21a) without ever being fixed — each time correctly identified but deprioritized as lower-value than that round's code work. The recurring rediscovery is itself the cost: every round that reads CLAUDE.md re-derives the same finding from scratch instead of building on a corrected doc, and this round's own initial investigation nearly proceeded on the stale model before verifying live code. This round already produced the exact, grep-verified facts needed (no more --pico-*/--tinta-* anywhere; all but two trivial redirect pages now use Panda css()/recipes; --s-*/--papel-* survive only as global aliases in web/src/index.css consumed by four specific Svelte components) as a side effect of investigating issue #1136, so the marginal cost of fixing it now is near zero and the accumulated benefit (no fifth rediscovery) is real."
success_signal: "CLAUDE.md's CSS section text matches the verified live architecture: names the cobogo/Panda preset and its config file, describes web/src/index.css as an alias bridge (not a second design system for a page category), names exactly which components still consume the legacy names, and removes the retired --pico-*/--tinta-* and page-type-boundary claims. A PR containing only this doc change (plus this round's OKF report) is opened and merged."
status: "achieved"
---

# Goal: corrigir a fronteira CSS obsoleta em CLAUDE.md

Reescrever a seção `### CSS token boundary` para refletir a arquitetura real (Panda CSS via preset `cobogo`, com um pequeno bridge de compatibilidade para quatro componentes Svelte ainda não convertidos), encerrando uma lacuna de documentação sinalizada por quatro rodadas seguidas sem nunca ter sido corrigida.
