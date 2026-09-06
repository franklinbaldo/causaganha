---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-3kjpfr-decision-svelte-no-panda-css-clarify-docs"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
question: "CLAUDE.md's CSS token boundary section says 'New pages/components: use Panda (css()/recipes...)'. TribunalCoverageExplorer.svelte is a brand-new, non-legacy component this round adds — should it import styled-system/css like an .astro page does?"
choice: "No — style it like every other Svelte component in the tree (DuckDBExplorer.svelte included, itself non-legacy) already does: recipes are fine, but raw css({...}) is not, so use plain global element-level CSS plus a small scoped <style> block with literal values, no custom properties. Also add one clarifying bullet to CLAUDE.md documenting why."
rationale: "Verified panda.config.ts's include glob is './src/**/*.{astro,js,jsx,ts,tsx}' — .svelte is not in it. grep across the whole web/src tree confirms zero Svelte components, legacy or not, import from styled-system. Panda's css() is extraction-based: a property/value combo only gets a real generated class if some included file's static analysis finds that call, so a css({...}) call written only inside a .svelte file produces a className string with no matching CSS rule (silently broken styling) — recipes are exempt because Panda pre-generates all of a recipe's variant CSS regardless of call site. CLAUDE.md's existing wording ('New pages/components: use Panda') is accurate for .astro pages but was silently misleading for a new Svelte component specifically, and nothing in the file explained why every existing Svelte component avoids css() even outside the four legacy islands. Fixed by adding one bullet to the same section (CLAUDE.md, not a new doc) rather than leaving the next round to rediscover this the hard way."
---

# Decisão: novo componente Svelte não usa `css()`, e a lacuna de documentação foi corrigida

`TribunalCoverageExplorer.svelte` usa apenas classes globais (`index.css`) e um `<style>` local com valores literais — nunca `css()` do Panda, porque `panda.config.ts` nunca varre arquivos `.svelte`. Adicionada uma frase em `CLAUDE.md` (`### CSS token boundary`) documentando essa lacuna, já que a redação anterior implicava (sem dizer explicitamente) que "novos componentes" deveriam usar `css()` incondicionalmente.
