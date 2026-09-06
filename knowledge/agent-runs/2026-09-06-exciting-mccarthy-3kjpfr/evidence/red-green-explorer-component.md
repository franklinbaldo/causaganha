---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-3kjpfr-evidence-red-green-explorer-component"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
kind: "test_green"
reference: "web/src/components/TribunalCoverageExplorer.svelte + web/src/components/TribunalCoverageExplorer.test.ts, run via `npx vitest run src/components/TribunalCoverageExplorer.test.ts`"
summary: "RED confirmed first: test-only commit failed with 'Failed to resolve import \"./TribunalCoverageExplorer.svelte\"'. GREEN after writing the component: 5/5 tests passed — default-period summary text, the 'sem evidência suficiente neste período' message when zero days are observed (never 0%), recomputation on tribunal-select change, URL querystring reflecting the new selection after a change, and a working link to /publicacoes/{tribunal} reusing that page's existing semantics. One implementation fix during GREEN: the summary text originally wrapped counts in <strong>, which testing-library's getByText could not match against the parent <p> (it only concatenates an element's own direct text nodes, not descendant element text) — removed the <strong> wrapping so the whole sentence is one run of sibling text nodes."
---

# Evidência: RED→GREEN do componente TribunalCoverageExplorer

Componente nasceu de teste vermelho (arquivo inexistente) para 5/5 verde, cobrindo o veredito por período, o caso de zero evidência, a reatividade à troca de tribunal, o espelhamento na URL e o link para o calendário completo do tribunal.
