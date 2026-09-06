---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-8a9dnj-decision-mock-clipboard-per-test"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
question: "How should tests stub the Clipboard API (navigator.clipboard.writeText), given jsdom's test environment does not define navigator.clipboard at all and no test in this codebase mocks it yet?"
choice: "Define a small per-test helper (stubClipboard) inside TribunalCoverageExplorer.test.ts that does Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true }) with a caller-supplied vi.fn() resolving or rejecting as needed, called once per test rather than in a shared beforeEach."
rationale: "Object.defineProperty with configurable: true is required because navigator.clipboard is undefined in this jsdom setup (a plain assignment `navigator.clipboard = ...` throws or silently no-ops depending on the property descriptor jsdom exposes for `navigator`, whereas defineProperty reliably (re)defines it). Scoping the stub per-test rather than in a shared beforeEach keeps each test's clipboard behavior (resolve vs. reject) explicit at its call site, matching this test file's existing style (mockFetch is also called per-test, not globally). No new test dependency was added — this uses only vi.fn(), already imported from vitest in this file."
---

# Decisão: stub do Clipboard API por teste, sem dependência nova

`navigator.clipboard` não existe no ambiente jsdom deste projeto e nenhum teste existente o mockava. Optei por um helper `stubClipboard` local ao arquivo de teste, usando `Object.defineProperty` (necessário porque a propriedade não existe de partida) e chamado por teste — não em um `beforeEach` compartilhado — para manter o comportamento (sucesso vs. falha) explícito em cada caso, no mesmo estilo já usado por `mockFetch` neste arquivo.
