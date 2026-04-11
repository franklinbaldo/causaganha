# Frontend Architecture Guide

This document describes our intended tech stack, how to use each technology idiomatically, how to combine them correctly, and the patterns we should follow and avoid.

All frontend code lives under `web/`.

---

## Design Principles

All frontend decisions must serve the principles in [`DESIGN.md`](DESIGN.md). Read it before touching any UI. The principles most directly relevant to code decisions:

- **HTML first, CSS second, JavaScript last.** Start from a document that works without scripting. Every `client:*` directive you add is a deliberate exception, not a default.
- **Speed is part of aesthetics.** Fast pages feel intelligent. Client-side JavaScript that isn't necessary is a performance regression, not neutral.
- **No appification of reading tasks.** This is a data-reading interface. Resist the impulse to add modals, carousels, and app-like patterns where a simple page would do.
- **Expose structure instead of hiding it.** Prefer tables, headings, and inline information over collapsed panels and hover-reveals.

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

<!-- Hydrates when the browser is idle (low priority). Use for non-critical UI
     that doesn't need to be interactive immediately after page load. -->
<MyComponent client:idle />
```

### Passing data into islands

Pass only serializable data (strings, numbers, plain objects) as props. Non-serializable values (functions, class instances) cannot cross the island boundary.

```astro
---
// web/src/pages/[tribunal].astro
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

### Three tiers of state

Choose the right tier for each piece of state:

**1. Component-local state** — `$state` / `$derived` inside a `<script>` block. Use for state that belongs entirely to one component instance.

**2. Cross-island shared state** — a `writable` store exported from a `.ts` file in `lib/`. Use when two or more Svelte islands on the same page need to read from or write to the same value.

```ts
// web/src/lib/workflowStatusStore.ts
import { writable } from 'svelte/store';

export const workflowStatus = writable<string | null>(null);
```

```svelte
<script lang="ts">
  import { workflowStatus } from '../lib/workflowStatusStore';
</script>

<p>{$workflowStatus}</p>
```

The `$` prefix auto-subscribes and auto-unsubscribes. Never manually call `.subscribe()` inside a component unless you also call the returned unsubscribe function in `onDestroy`.

**3. Singleton lazy-loader** — module-level `$state` runes inside a `.svelte.ts` file. Use for shared data that should be fetched once and shared reactively across any component that imports it. The file extension **must be `.svelte.ts`** for runes to work outside of `.svelte` components.

```ts
// web/src/lib/completedItemsStore.svelte.ts
let _data = $state<Record<string, any> | null>(null);
let _loading = $state(true);
let _initialized = false;

function ensureLoaded() {
  if (_initialized || typeof window === 'undefined') return;
  _initialized = true;
  fetch('...')
    .then(r => r.json())
    .then(json => { _data = json; })
    .finally(() => { _loading = false; });
}

export const myStore = {
  get data()    { return _data; },
  get loading() { return _loading; },
  load: ensureLoaded,
};
```

Any component that imports `myStore` reads reactive state directly — no subscription boilerplate needed.

### Props — use `$props()` rune in Svelte 5

```svelte
<script lang="ts">
  interface Props {
    tribunal: string;
    count?: number;
  }

  let { tribunal, count = 0 }: Props = $props();
</script>
```

### Component style isolation

Every `.svelte` file scopes its `<style>` block to the component. Do not add global selectors inside a component's `<style>` unless you wrap them in `:global()` explicitly and have a clear reason.

Design token CSS variables (defined in `web/src/index.css`) are available everywhere — use them, do not hardcode colors or spacing values.

### Anti-patterns — Svelte

- **Do not** use `$effect` to derive computed values — use `$derived` for that. `$effect` is for side effects only (logging, DOM manipulation, external subscriptions).
- **Do not** write to a `$state` variable inside the `$derived` that reads it. That creates a cycle.
- **Do not** store mutable class instances in `$state` if you want fine-grained reactivity. Svelte tracks object identity, not deep mutations. Use plain objects or arrays.
- **Do not** create stores inside components. Stores belong in `lib/`. A store created inside a component is re-created on every mount.
- **Do not** reach for `onMount` just to set initial state — use `$state` initialization or `$derived` instead.
- **Do not** use a `.svelte.ts` file extension unless you actually need module-level runes. Plain logic belongs in `.ts`.

---

## Vanilla CSS and Design Tokens

All global design tokens are in `web/src/index.css`. Every token is a CSS custom property on `:root`.

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

### Tailwind migration status

Tailwind has been **removed from the toolchain** — it is not in `package.json`. However, some existing components still contain legacy utility class strings (`bg-*`, `text-*`, `p-*`, `flex`, etc.) from before the migration. A migration script exists at `web/strip-tailwind-classes.mjs`.

Rules for contributors:
- **Never add new Tailwind/utility classes.** Always write vanilla CSS using design tokens.
- If you are editing a component that still has legacy utility classes, migrate those classes to CSS variables in the same PR. Do not leave mixed styles.
- If you see `class="bg-gray-100 p-4"` in a file you are touching, replace it with a scoped CSS rule using `var(--color-base-100)` and `var(--space-4)`.

### Responsive design

Use a mobile-first approach. Write the default styles for small screens and add `@media (min-width: ...)` for larger breakpoints.

### Anti-patterns — CSS

- **Do not** write inline `style="..."` with hardcoded values. Use tokens via CSS classes or CSS variables.
- **Do not** use `!important`. If specificity is a problem, restructure the selectors.
- **Do not** add new one-off color values. Extend the token set in `index.css` if a new semantic color is needed.
- **Do not** duplicate token values by copy-pasting hex codes. Always reference the variable.

---

## Zod

Zod is used to validate all external data at the boundary — API responses, URL query parameters, JSON files. The canonical patterns are established in `web/src/lib/djen.ts`.

### Always validate at the boundary

```ts
import { z } from 'zod';

const JulgamentoSchema = z.object({
  id: z.string(),
  tribunal: z.string(),
  data: z.string().optional(),
  resultado: z.enum(['procedente', 'improcedente', 'parcialmente_procedente']),
});

// Derive the type from the schema — never from itself
type Julgamento = z.infer<typeof JulgamentoSchema>;

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

## DOMPurify

Judicial publications from the DJEN API arrive as raw HTML strings. They may contain unsafe markup. Before rendering any HTML string with Svelte's `{@html ...}`, always sanitize with DOMPurify. The pattern is established in `web/src/lib/djen.ts`.

```svelte
<script lang="ts">
  import DOMPurify from 'dompurify';

  const { rawHtml }: { rawHtml: string } = $props();
  const safeHtml = DOMPurify.sanitize(rawHtml);
</script>

<div>{@html safeHtml}</div>
```

**Anti-pattern:**

```svelte
<!-- Never do this — XSS vulnerability -->
<div>{@html publication.texto}</div>
```

---

## State Architecture — Combining Svelte Stores with Astro Islands

The hardest problem in this architecture is sharing state between Svelte islands that Astro treats as independent component trees.

### The shared store pattern

Islands share state by importing the same store module. Because modules are singletons in the browser, both islands read from and write to the same store instance.

See `web/src/lib/workflowStatusStore.ts` for a simple example and `web/src/lib/completedItemsStore.svelte.ts` for the singleton lazy-loader variant.

### The `createDataRefresh` factory

`web/src/lib/dataRefreshStore.ts` exports a factory for islands that need auto-refreshing data:

```ts
import { createDataRefresh } from '../lib/dataRefreshStore';

// key: the property name in the shared data payload
// initialData: server-rendered seed data (optional)
// interval: polling interval in ms (default 60 000)
const store = createDataRefresh('tribunais', serverData, 60_000);
store.start(); // fetches immediately, then polls
```

The factory returns a Svelte store with shape `{ data, loading, error }` plus `refresh()`, `start()`, and `stop()` methods.

Internally it maintains `window.__CAUSAGANHA_DATA` — a client-side cache with a 15-second TTL that deduplicates in-flight requests. Multiple islands on the same page that call `createDataRefresh` will share one underlying fetch, not issue parallel requests.

Use `createDataRefresh` when the island needs:
- Auto-polling with a configurable interval
- Shared caching across other islands on the page

Use a plain `writable` store when the data is local to one island or managed by user interaction, not periodic fetch.

### Anti-patterns — State

- **Do not** pass state between islands via Astro props after the page loads. Props are static; they cannot react to changes. Use a store.
- **Do not** store fetched data in a plain module-level `let` variable. It will not be reactive. Use a store.
- **Do not** use `localStorage` as the primary state mechanism. Use a store and persist to `localStorage` only for user preferences (theme, etc.) that need to survive page reloads.

---

## Data Fetching

All data fetching goes through `web/src/lib/fetchData.ts`, which implements retry logic and error handling. Do not call `fetch()` directly in components.

The file exports:
- `fetchWithRetry(url)` — single URL fetch with exponential-backoff retry
- `fetchAllData()` — fetches the full derived dataset (used by `createDataRefresh`)
- `startLivePolling(onUpdate, intervalMs)` — starts a polling loop, returns a stop function
- `deriveData(stats, dashboardData, cacheData, tribunalStartDates?, tribunalQualityScores?, perfMetrics?, iaSnapshot?)` — pure transformation that merges multiple data sources into the `DerivedData` shape; used in Astro pages at build time

```ts
// Correct — use the exported helpers
import { fetchWithRetry } from '../lib/fetchData';
const result = await fetchWithRetry('/api/julgamentos');

// Wrong — bypasses retry logic and error handling
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

Used for data visualization (heatmaps, coverage charts). Always render Plot inside a Svelte `$effect` — Plot requires the DOM.

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

Feature-level behavior is specified in Gherkin `.feature` files under `web/features/`. Step definitions live separately under `web/src/components/__steps__/`. Keep these two directories separate.

```
web/
├── features/
│   ├── homepage.feature
│   └── publicacoes.feature   ← .feature files go here
└── src/components/__steps__/
    ├── homepage.steps.tsx
    └── publicacoes.steps.ts  ← step definitions go here
```

Step files load their feature using a path relative to the project root:

```ts
import { loadFeature, describeFeature } from '@amiceli/vitest-cucumber';

const feature = await loadFeature('features/homepage.feature');

describeFeature(feature, ({ Scenario }) => {
  // ...
});
```

Keep step definitions thin — they should call the same Testing Library queries used in unit tests.

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

## Known Gaps

These areas are not yet covered by existing infrastructure. Be aware before assuming they exist.

- **No end-to-end tests.** Playwright or a similar e2e framework is not set up. BDD tests run in jsdom only and do not test real browser behavior or full page navigation.
- **No i18n.** All UI strings are hardcoded in Portuguese. There is no translation framework in place.
- **Accessibility.** Guidelines and known gaps are documented in `web/ACCESSIBILITY.md` and `web/ACCESSIBILITY_IMPROVEMENTS_NEEDED.md`. Read both before modifying any UI component — do not introduce new accessibility regressions.

---

## Summary: The Decision Ladder

When adding a new piece of code, ask these questions in order:

1. **Is this logic with no UI?** → `lib/` as a `.ts` file.
2. **Is this a Zod schema or type definition?** → `lib/` alongside the fetcher that uses it.
3. **Is this a singleton store or lazy-loader?** → `lib/` as a `.svelte.ts` file (module-level `$state`).
4. **Is this shared reactive state between islands?** → `lib/` as a plain `.ts` file with a `writable` store.
5. **Is this static HTML with at most one trivial DOM interaction?** → `.astro` with a plain `<script>`.
6. **Is this interactive UI with reactive state?** → `.svelte` component, added to a page as an island with the least-expensive `client:*` directive that still works.

Every line of client-side JavaScript is a cost. Always start at step 1 and only move down the ladder when the simpler option is insufficient.
