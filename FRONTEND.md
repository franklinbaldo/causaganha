# Frontend Architecture Guide

This document describes our intended tech stack, how to use each technology idiomatically, how to combine them correctly, and the patterns we should follow and avoid.

All frontend code lives under `dashboard/`.

---

## Tech Stack Overview

| Layer | Technology |
|---|---|
| Meta-framework | Astro 5 |
| Component framework | Svelte 5 |
| Styling | Vanilla CSS with design tokens |
| State | Svelte stores + Svelte 5 runes |
| Build | Vite |
| Validation | Zod |
| Data viz | Observable Plot |
| In-browser SQL | DuckDB WASM |
| Sanitization | DOMPurify |
| Testing | Vitest + Testing Library + vitest-cucumber |
| Linting | ESLint (flat config) + TypeScript |

---

## When to Create `.astro` vs `.svelte` vs Neither

This is the most consequential decision in this codebase. Getting it wrong adds unnecessary JavaScript to the page.

### Create a `.astro` file when

- The output is **purely static** — no user interaction after page load.
- Interactivity is **light DOM manipulation** that a plain `<script>` tag handles easily (example: `ThemeToggle.astro` uses `addEventListener` and `localStorage` without any Svelte overhead).
- You are building a **layout**, **page**, or **structural shell** — headers, footers, breadcrumbs, page wrappers.
- You need to **compose islands**: `.astro` files are the correct host that decides which Svelte components get hydrated and which don't.

### Create a `.svelte` file when

- The component has **reactive state** that changes after the page loads.
- The component needs **Svelte stores** or **rune-based reactivity** (`$state`, `$derived`).
- The component is **interactive enough** that DOM manipulation via plain scripts would become messy (conditional rendering, lists that update, derived display values).
- The component will be reused **across multiple pages with shared state**.

### Create neither — put it in `lib/` when

- The concern is **pure logic**: data fetching, validation, transformation, calculations.
- The code is **framework-agnostic** and could in principle be used by both `.astro` and `.svelte` files.
- You are defining a **Zod schema**, a **store**, or a **utility function**.

### Decision flowchart

```
Does it render HTML?
├─ No  → lib/ (utility, store, schema)
└─ Yes → Does it need reactive state after page load?
         ├─ No  → Is interactivity trivial (one listener, no derived state)?
         │        ├─ Yes → .astro with plain <script>
         │        └─ No  → .svelte (client:load or client:visible)
         └─ Yes → .svelte
```

---

## Astro

### Island architecture — the core mental model

Astro renders every component to static HTML at build time. A Svelte component only runs on the client if you add a `client:*` directive. Treat each directive as a cost you are deliberately paying:

```astro
<!-- Zero JS — just HTML. Always prefer this when possible. -->
<MyComponent />

<!-- Hydrates immediately on page load. Use for above-the-fold interactive UI. -->
<MyComponent client:load />

<!-- Hydrates when the component enters the viewport. Use for below-the-fold UI. -->
<MyComponent client:visible />

<!-- Hydrates on first user interaction. Use for things like dropdowns. -->
<MyComponent client:idle />
```

### Passing data into islands

Pass only serializable data (strings, numbers, plain objects) as props. Non-serializable values (functions, class instances) cannot cross the island boundary.

```astro
---
// dashboard/src/pages/[tribunal].astro
import HeatmapIsland from '../components/Heatmap.svelte';
const data = await fetchSomeData();
---
<HeatmapIsland data={data} client:visible />
```

### View Transitions

This project uses Astro's View Transitions API. Any vanilla `<script>` that runs on page load must also re-run after a transition:

```astro
<script>
  function setup() { /* ... */ }

  setup();
  document.addEventListener('astro:after-swap', setup);
</script>
```

Forgetting `astro:after-swap` is the most common bug with view transitions.

### Anti-patterns — Astro

- **Do not** add `client:load` to components that have no client-side interactivity. Static components ship zero JS by default; adding a directive breaks that.
- **Do not** use Astro component `<script>` tags to manage complex state. Reach for Svelte instead.
- **Do not** import server-only Node modules inside components used with SSG — the build will fail at deploy time.
- **Do not** use `client:only` unless unavoidable (DuckDB WASM is a valid exception because it requires the browser environment). `client:only` skips server-side rendering entirely and hurts initial load.

---

## Svelte 5

### Runes — prefer them for local component state

Svelte 5 introduces runes. Use them instead of the legacy `let` + reactive syntax:

```svelte
<script lang="ts">
  // Local reactive state
  let count = $state(0);

  // Derived value — recalculates automatically
  let doubled = $derived(count * 2);

  // Side effect — runs when dependencies change
  $effect(() => {
    console.log('count changed:', count);
  });
</script>
```

Do not mix the Svelte 4 `$:` reactive statements with Svelte 5 runes in the same component.

### Svelte stores — for shared cross-island state

When two Svelte islands on the same page need to share state, use a writable store defined in `lib/`:

```ts
// dashboard/src/lib/workflowStatusStore.ts
import { writable } from 'svelte/store';

export const workflowStatus = writable<string | null>(null);
```

```svelte
<!-- Inside any Svelte component -->
<script lang="ts">
  import { workflowStatus } from '../lib/workflowStatusStore';
</script>

<p>{$workflowStatus}</p>
```

The `$` prefix auto-subscribes and auto-unsubscribes. Never manually call `.subscribe()` inside a component unless you also call the returned unsubscribe function in `onDestroy`.

### Props — use `$props()` rune in Svelte 5

```svelte
<script lang="ts">
  interface Props {
    tribunal: string;
    count?: number;
  }

  const { tribunal, count = 0 }: Props = $props();
</script>
```

### Component style isolation

Every `.svelte` file scopes its `<style>` block to the component. Do not add global selectors inside a component's `<style>` unless you wrap them in `:global()` explicitly and have a clear reason.

Design token CSS variables (defined in `dashboard/src/index.css`) are available everywhere — use them, do not hardcode colors or spacing values.

### Anti-patterns — Svelte

- **Do not** use `$effect` to derive computed values — use `$derived` for that. `$effect` is for side effects only (logging, DOM manipulation, external subscriptions).
- **Do not** write to a `$state` variable inside the `$derived` that reads it. That creates a cycle.
- **Do not** store mutable class instances in `$state` if you want fine-grained reactivity. Svelte tracks object identity, not deep mutations. Use plain objects or arrays.
- **Do not** create stores inside components. Stores belong in `lib/`. A store created inside a component is re-created on every mount.
- **Do not** reach for `onMount` just to set initial state — use `$state` initialization or `$derived` instead.

---

## Vanilla CSS and Design Tokens

All global design tokens are in `dashboard/src/index.css`. Every token is a CSS custom property on `:root`.

### Use tokens — never hardcode

```css
/* Correct */
.card {
  padding: var(--space-4);
  background: var(--color-base-100);
  border-radius: var(--radius-card);
  font-size: var(--font-size-sm);
}

/* Wrong */
.card {
  padding: 16px;
  background: #1a1a2e;
  border-radius: 8px;
  font-size: 14px;
}
```

### Theming

The theme is applied via `data-theme` on `<html>`. Both `causaganha` (light) and `causaganhadark` (dark) themes are defined as attribute selectors in `index.css`. Components automatically respond to theme changes because they use CSS variables.

### Responsive design

Use a mobile-first approach. Write the default styles for small screens and add `@media (min-width: ...)` for larger breakpoints.

### Anti-patterns — CSS

- **Do not** write inline `style="..."` with hardcoded values. Use tokens via CSS classes or CSS variables.
- **Do not** use `!important`. If specificity is a problem, restructure the selectors.
- **Do not** add new one-off color values. Extend the token set in `index.css` if a new semantic color is needed.
- **Do not** duplicate token values by copy-pasting hex codes. Always reference the variable.

---

## Zod

Zod is used to validate all external data at the boundary — API responses, URL query parameters, JSON files. The canonical patterns are established in `dashboard/src/lib/djen.ts`.

### Always validate at the boundary

```ts
import { z } from 'zod';

const JulgamentoSchema = z.object({
  id: z.string(),
  tribunal: z.string(),
  data: z.string().optional(),
  resultado: z.enum(['procedente', 'improcedente', 'parcialmente_procedente']),
});

type Julgamento = z.infer<typeof Julgamento>;

const raw = await res.json();
const julgamento = JulgamentoSchema.parse(raw); // throws on invalid data
```

Use `.parse()` when failure should throw (API responses where bad data is a bug). Use `.safeParse()` when you want to handle validation failure gracefully in the UI.

### Coerce messy API data with `z.preprocess`

The API data in this project is inconsistent — numbers arrive as strings, nulls arrive where values are expected. Follow the pattern in `djen.ts`:

```ts
const optionalNumber = z.preprocess((value) => {
  if (value === null || value === undefined || value === '') return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}, z.number().optional());
```

### Derive TypeScript types from schemas — never duplicate them

```ts
// Define once
const Schema = z.object({ ... });

// Derive the type — do NOT write a separate interface that mirrors this
type MyType = z.infer<typeof Schema>;
```

### Anti-patterns — Zod

- **Do not** cast API data with `as MyType` instead of parsing it. That defeats the entire purpose.
- **Do not** define a TypeScript interface that mirrors a Zod schema. Derive the type with `z.infer<>`.
- **Do not** put Zod schemas inside components. They belong in `lib/`.
- **Do not** use `.parse()` inside a render loop where a validation error would crash the component. Use `.safeParse()` and handle the error case.

---

## State Architecture — Combining Svelte Stores with Astro Islands

The hardest problem in this architecture is sharing state between Svelte islands that Astro treats as independent component trees.

### The shared store pattern

Islands share state by importing the same store module. Because modules are singletons in the browser, both islands read from and write to the same store instance:

```ts
// lib/dataRefreshStore.ts — singleton, lives outside any component
export const refreshTrigger = writable(0);
```

```svelte
<!-- Island A: triggers a refresh -->
<script lang="ts">
  import { refreshTrigger } from '../lib/dataRefreshStore';
  function refresh() { refreshTrigger.update(n => n + 1); }
</script>
```

```svelte
<!-- Island B: reacts to refreshes -->
<script lang="ts">
  import { refreshTrigger } from '../lib/dataRefreshStore';

  $effect(() => {
    const _ = $refreshTrigger; // subscribe to trigger
    loadData();
  });
</script>
```

### Client-side cache

`dataRefreshStore.ts` implements a 15-second stale-time cache on `window`. This prevents duplicate API calls when multiple islands fetch the same data. Always go through this cache for shared data fetches rather than calling `fetch()` directly.

### Anti-patterns — State

- **Do not** pass state between islands via Astro props after the page loads. Props are static; they cannot react to changes. Use a store.
- **Do not** store fetched data in a plain module-level `let` variable. It will not be reactive. Use a store.
- **Do not** use `localStorage` as the primary state mechanism. Use a store and persist to `localStorage` only for user preferences (theme, etc.) that need to survive page reloads.

---

## Data Fetching

All data fetching goes through `dashboard/src/lib/fetchData.ts`, which implements retry logic and error handling. Do not call `fetch()` directly in components.

```ts
// Correct
import { fetchData } from '../lib/fetchData';
const result = await fetchData('/api/julgamentos');

// Wrong
const result = await fetch('/api/julgamentos').then(r => r.json());
```

Pair every fetch with a Zod schema parse so that bad data surfaces immediately as a validation error rather than silently corrupting the UI.

---

## DuckDB WASM

DuckDB runs entirely in the browser via WASM. It is used for the SQL explorer interface and for client-side analytical queries over downloaded datasets.

Because DuckDB requires the browser environment, any component that uses it must be a Svelte island with `client:only="svelte"`. There is no server-side counterpart.

Keep DuckDB initialization in a single place (do not spin up multiple instances). The instance should be created once and shared via a module-level singleton.

---

## Observable Plot

Used for data visualization (heatmaps, coverage charts). Always render Plot inside `onMount` or a Svelte `$effect` — Plot requires the DOM.

```svelte
<script lang="ts">
  import * as Plot from '@observablehq/plot';

  let container: HTMLDivElement;

  $effect(() => {
    if (!container || !data) return;

    const chart = Plot.plot({ /* ... */ });
    container.replaceChildren(chart);

    return () => chart.remove(); // cleanup
  });
</script>

<div bind:this={container}></div>
```

The cleanup return value inside `$effect` prevents stale charts from accumulating on re-renders.

---

## Testing

### Unit tests — Vitest + Testing Library

Test utilities and store logic with plain Vitest unit tests. Test Svelte components with `@testing-library/svelte`, which renders into jsdom.

```ts
import { render, screen } from '@testing-library/svelte';
import MyComponent from './MyComponent.svelte';

test('shows tribunal name', () => {
  render(MyComponent, { props: { tribunal: 'TJSP' } });
  expect(screen.getByText('TJSP')).toBeInTheDocument();
});
```

### BDD tests — vitest-cucumber

Feature-level behavior is specified in Gherkin `.feature` files under `src/components/__steps__/`. This is the right place to describe user-facing behavior.

```gherkin
Feature: Publication search
  Scenario: User searches for a tribunal
    Given the search input is visible
    When the user types "TJSP"
    Then the results list shows publications from TJSP
```

Write step definitions in the corresponding `*.steps.ts` file. Keep step definitions thin — they should call the same Testing Library queries used in unit tests.

### Anti-patterns — Testing

- **Do not** test implementation details (internal store values, private functions). Test observable behavior.
- **Do not** skip the `astro:after-swap` event in tests for components that use it — simulate it or test after setting up the DOM correctly.
- **Do not** write feature files that describe how the code works rather than what the user experiences.

---

## TypeScript

The project uses strict TypeScript (`astro/tsconfigs/strict`). All `.svelte` files use `<script lang="ts">`.

- Prefer `type` over `interface` for data shapes derived from Zod schemas.
- Use `interface` for things that may be extended (component prop shapes that other code might augment).
- Never use `any`. Use `unknown` when the type is genuinely unknown and then narrow it.
- Do not use non-null assertion (`!`) except where the value is structurally guaranteed (e.g., immediately after a null-check guard at the top of a function).

---

## Summary: The Decision Ladder

When adding a new piece of code, ask these questions in order:

1. **Is this logic with no UI?** → `lib/` as a `.ts` file.
2. **Is this a Zod schema or type definition?** → `lib/` alongside the fetcher that uses it.
3. **Is this a store?** → `lib/` as a `.ts` or `.svelte.ts` file.
4. **Is this static HTML with at most one trivial DOM interaction?** → `.astro` with a plain `<script>`.
5. **Is this interactive UI with reactive state?** → `.svelte` component, added to a page as an island with the least-expensive `client:*` directive that still works.

Every line of client-side JavaScript is a cost. Always start at step 1 and only move down the ladder when the simpler option is insufficient.
