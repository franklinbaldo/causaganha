# Frontend Architecture Guide

This document describes our intended tech stack, how to use each technology idiomatically, how to combine them correctly, and the patterns we should follow and avoid.

All frontend code lives under `web/`.

---

## Design Principles

All frontend decisions must serve the [Design Constitution](#design-constitution) at the end of this document. Read it before touching any UI. The principles most directly relevant to code decisions:

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
| Styling | Pico CSS (semantic baseline) + Vanilla CSS with design tokens |
| Async state / data fetching | TanStack Query (`@tanstack/svelte-query@^6`) |
| Local state | Svelte 5 runes (`$state`, `$derived`) |
| Cross-island shared state | Svelte stores (`writable`) |
| Build | Vite |
| Validation | Zod |
| Data viz | Observable Plot |
| In-browser SQL | DuckDB WASM |
| Sanitization | DOMPurify |
| Testing | Vitest + Testing Library + vitest-cucumber |
| Linting | ESLint (flat config) |
| Language | TypeScript (strict) |

---

## Deployment — GitHub Pages (SSG)

This project is deployed as a **100% static site on GitHub Pages** via `output: 'static'` in `astro.config.mjs`. Key constraints that affect every frontend decision:

- **No server at runtime.** There are no API routes, no SSR, no middleware. Every page is a `.html` file generated at build time.
- **`readJson()` runs only at build time and returns `null` on missing or malformed files.** It does not throw — it silently returns `null`. Always handle the null case in Astro pages; never assume the file exists.
- **All dynamic routes must use `getStaticPaths()`.** There is no server fallback for unknown paths. If a path is not in `getStaticPaths()`, it does not exist.
- **`404.astro` is the GitHub Pages 404 page.** GitHub Pages serves `404.html` for unknown paths automatically — no extra configuration needed.
- **Always use `import.meta.env.BASE_URL`, never hardcode `/causaganha/`.** The base path is `/causaganha` in production; hardcoded paths break local dev.

```ts
// Correct
const href = import.meta.env.BASE_URL + 'publicacoes';

// Wrong — breaks on local dev, breaks if base path ever changes
const href = '/causaganha/publicacoes';
```

- **`trailingSlash: 'never'`** — internal `href` values must not end with `/`. Write `href={BASE_URL + 'publicacoes'}`, not `href={BASE_URL + 'publicacoes/'}`.
- **Prefetch is on by default (`defaultStrategy: 'hover'`).** Links prefetch on hover automatically. Do not add manual `<link rel="prefetch">` tags.
- **The primary data source is Internet Archive, not a backend.** After the static page loads, `fetchData.ts` fetches live JSON from `archive.org`. Some components also call the GitHub API directly (e.g. `workflowStatusStore.ts`, `PipelineRunHistory.svelte`) for pipeline status — these are valid exceptions, not violations of this rule.
- **`.ts` endpoint files generate static files at build.** `robots.txt.ts` and `sitemap.xml.ts` run once at build time and output static files. They are not runtime API routes.

### Anti-patterns — Deployment

- **Do not** use `Astro.request`, `Astro.response`, or server middleware — they require SSR.
- **Do not** use `client:server-only` or any Astro SSR-only feature.
- **Do not** expect `readJson()` to work inside Svelte components (browser context). It is build-time only.
- **Do not** hardcode `/causaganha/` — use `import.meta.env.BASE_URL`.

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

### `lib/` organisation

`lib/` is intentionally flat — specific filenames convey purpose without needing sub-directories. Current logical groups:

| Group | Files |
|---|---|
| Core data fetching | `fetchData.ts`, `readJson.ts`, `buildTimeData.ts`, `duckdbSingleton.ts` |
| TanStack Query / async state | `queryClient.ts`, `queryKeys.ts`, `useDashboard.svelte.ts` |
| Svelte stores | `completedItemsStore.svelte.ts`, `workflowStatusStore.ts` |
| Search & query | `djen.ts`, `djenClient.ts`, `searchQueryString.ts` |
| Utilities | `colorUtils.ts`, `dateUtils.ts`, `velocityCalc.ts`, `iaMetadataFetcher.ts`, `stats-processing.ts` |
| Reference data | `tribunais.ts`, `homepage-content.ts` |

New files should fit into one of these groups by name. Sub-directories are not needed unless a group grows past ~6 files.

### Decision flowchart

```
Does it render HTML?
├─ No  → lib/ (utility, store, schema)
└─ Yes → Does it need ANY client-side JS?
         ├─ No  → .astro with no <script> (zero JS — preferred default)
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
- **Do not** use `client:only` unless unavoidable. `client:only` skips server-side rendering entirely and hurts initial load. When you must use it, always include the framework string: `client:only="svelte"`. DuckDB WASM is the canonical valid exception because it requires the browser environment.

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

### Four tiers of state

Choose the right tier for each piece of state:

**0. Build-time static seed** — Astro pages run at **build time** (not at request time, because this site is static). They read local JSON via `readJson()`, merge it through `deriveData()` to produce the canonical `DerivedData` shape, and pass specific fields of that shape as typed `initialXxx` props to Svelte islands. The island calls `useDashboardWithPolling()` to get live data via TanStack Query, falling back to the build-time seed until the first fetch completes:

```astro
---
// web/src/pages/publicacoes/[tribunal].astro (runs at BUILD TIME)
import { loadBuildTimeData } from '../../lib/buildTimeData';

const data = loadBuildTimeData();
---
<TribunalDetail
  client:only="svelte"
  tribunalCode={tribunalCode}
  initialCoverage={data.tribunalCoverage}
  initialEtas={data.tribunalEtas}
/>
```

```svelte
<!-- web/src/components/TribunalDetail.svelte (runs in the BROWSER) -->
<script lang="ts">
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';

  let { initialCoverage } = $props();
  const dashboard = useDashboardWithPolling();  // sets context + creates query

  // Falls back to build-time seed until live refresh arrives
  let coverage = $derived(dashboard.data?.tribunalCoverage ?? initialCoverage);
</script>
```

The seed and the live-refresh shape must match exactly — that is why the page derives both through `deriveData()` rather than passing raw JSON. Always pass build-time data as `initialXxx` props when the page has it. Never leave an island with `null` initial state when the page can pre-populate it — the skeleton flash is user-visible and avoidable.

> **`buildTimeData.ts` is server-only.** `loadBuildTimeData()` imports `readJson()` which uses `node:fs`. **Only `.astro` frontmatter may import this module** — never `.svelte` files, never `.svelte.ts` stores, never any `.ts` reachable from client code. Adding it to `fetchData.ts` would pull `node:fs` into the browser bundle and break the build.

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

## Pico CSS — Semantic HTML as the First Styling Layer

Pico CSS is the visual baseline. It styles **native HTML elements directly** — no framework classes required for the common cases. The workflow is:

1. Write semantically correct HTML.
2. Pico provides the visual styling for free.
3. Add custom classes only for what Pico cannot express idiomatically.

This means **element choice is a styling decision.** Picking the wrong element defeats Pico's mapping and often breaks accessibility at the same time.

### Semantic patterns Pico expects

| Pattern | Correct | Wrong |
|---|---|---|
| Grouped radio / checkbox inputs | `<fieldset><legend>Label</legend>` | `<div><small>Label</small>` |
| Search input wrapper | `<search>` | `<div class="search-wrapper">` |
| Card container | `<article>` with `<header>` / `<footer>` | `<div class="card">` |
| Highlighted / status badge | `<mark data-tone="warning">` | `<span class="badge warning">` |
| Supporting metadata | `<small>` (within flow) | Used as group label substitute |
| Inline aria-busy loading hint | `<p aria-busy="true">` | `<div class="spinner">` |

### Elements used for semantic meaning only

These elements carry meaning beyond their visual appearance. Pico styles them, but **use them only when their meaning applies.**

| Element | Correct use | Wrong use |
|---|---|---|
| `<kbd>` | Keyboard input the user types (`Ctrl+K`) | Numeric badges, counts, visual chips |
| `<nav>` | Site navigation landmarks (main menu, breadcrumb, pagination) | Groups of action buttons (download, share, view) |
| `<data value="...">` | Machine-readable numeric or structured value alongside human text | Visual number display with no machine-readable need |
| `<small>` | Fine print, metadata captions, supporting context | Substitute for `<legend>` inside a `<fieldset>` |

#### Why `<nav>` is not for action groups

`<nav>` creates a landmark region that screen readers list alongside `<main>`, `<header>`, and `<footer>`. A cluster of action buttons (e.g. "Baixar ZIP / Compartilhar / Ver no IA") is not a navigation landmark — it is a toolbar or a button group. Use `<div aria-label="...">` or, if the keyboard interaction warrants it, `<div role="toolbar" aria-label="...">`.

#### Why `<kbd>` is not for visual badges

`<kbd>` tells assistive technology that the enclosed text represents a key the user should press. A screen reader navigating a ranking list will announce `<kbd>42</kbd>` as "press 42" — which is wrong. Use `<data value={n}>{n}</data>` for structured numeric output, or a plain `<span>` with a visual class.

#### Why `<fieldset>` + `<legend>` for radio / checkbox groups

Pico CSS styles `<fieldset>` as a clean grouped block and `<legend>` as the group's visible label. Using `<div>` + `<small>` loses the semantic grouping, breaks screen-reader announcement of which radio group is active, and foregoes Pico's default styling at the same time.

### Keyboard shortcut hints inside form labels

Do not put `<kbd>` elements inside a `<label>` — they become part of the accessible name of the associated input. A screen reader will announce "Buscar publicações Control K" as the field name. Keep `<kbd>` hints outside the `<label>`, use `aria-hidden="true"` on their wrapper, and position them visually with CSS:

```html
<!-- Correct -->
<search>
  <label>
    <input type="search" aria-label="Buscar publicações" />
  </label>
  <span class="search-shortcut-hint" aria-hidden="true"><kbd>Ctrl</kbd><kbd>K</kbd></span>
</search>

<!-- Wrong — "Buscar publicações Control K" becomes the field's accessible name -->
<label>
  <input type="search" aria-label="Buscar publicações" />
  <kbd>Ctrl</kbd><kbd>K</kbd>
</label>
```

### Anti-patterns — Pico CSS

- **Do not** use `<kbd>` as a badge or counter. Use `<data value={n}>{n}</data>` or a `<span>`.
- **Do not** use `<div>` + `<small>` to label radio or checkbox groups. Use `<fieldset>` + `<legend>`.
- **Do not** use `<nav>` for action button clusters. `<nav>` is a landmark — reserve it for navigation.
- **Do not** put `<kbd>` hints inside `<label>` elements. They pollute the accessible name of the input.
- **Do not** write `style="background: #1A6B3C; display: inline-block; ..."` for things that should be CSS classes. Inline colors ignore `[data-theme="dark"]` and can't be overridden by the design token system.
- **Do not** invent custom button classes for what Pico already expresses: use `.secondary`, `.outline`, `.secondary.outline` before adding a new class.

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

**Done-state:** The migration is complete when this command returns no matches:

```sh
rg -nP 'class="(?:[^"]*\s)?(bg-(?:white|black|[a-z]+-[0-9]+)|text-(?:xs|sm|base|lg|xl|[0-9]xl|white|black|center|left|right|[a-z]+-[0-9]+)|flex(?:-(?:row|col|wrap|nowrap))?|grid(?:-cols-[0-9]+)?|items-(?:start|center|end|stretch|baseline)|justify-(?:start|center|end|between|around|evenly)|gap(?:-[xy])?-[0-9]+|[pm][xytrbl]?-[0-9]+)(?=\s|")' web/src/components/
```

The regex uses PCRE (`rg -P`) with an explicit left boundary — the utility must be at the start of `class="..."` or preceded by whitespace — and a lookahead requiring whitespace or the closing quote on the right. This is what rules out custom class names that merely contain the substrings `grid`, `flex`, `items-...`, etc. (for example `mp-grid`, `summary-grid`, `story-grid` are correctly ignored). If you introduce a legitimate one-off class whose name collides with this pattern, audit the hit manually. Once the command returns zero matches, `web/strip-tailwind-classes.mjs` can be deleted.

### Responsive design

Use a mobile-first approach. Write the default styles for small screens and add `@media (min-width: ...)` for larger breakpoints.

### Anti-patterns — CSS

- **Do not** write inline `style="..."` with hardcoded values. Use tokens via CSS classes or CSS variables. Inline colors are invisible to `[data-theme="dark"]` and cannot be overridden.
- **Do not** use `!important`. If specificity is a problem, restructure the selectors.
- **Do not** add new one-off color values. Extend the token set in `index.css` if a new semantic color is needed.
- **Do not** duplicate token values by copy-pasting hex codes. Always reference the variable.
- **Do not** write CSS utility classes for visual states that Pico already handles via element/attribute selectors. Check Pico's documentation before adding a class. See the [Pico CSS section](#pico-css--semantic-html-as-the-first-styling-layer) for canonical idioms.

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

### TanStack Query for async state

All async data fetching in islands uses [TanStack Query](https://tanstack.com/query) (`@tanstack/svelte-query@^6`). It replaces the old `createDataRefresh` factory and provides deduplication, caching, background refetching, and retries out of the box.

#### Astro islands challenge — context per island

Each `client:*` island is an isolated Svelte component tree with no shared top-level provider. TanStack Query needs a `QueryClient` in Svelte context before any `createQuery` call. The solution is:

1. **Singleton QueryClient** (`web/src/lib/queryClient.ts`) — a module-level instance shared via ES module semantics across all islands on the page.
2. **`setQueryClientContext` in every island** — called synchronously at the top of each island's `<script>` block (before `createQuery`). Because all islands call `getQueryClient()`, they all receive the same instance and share the same cache.

```svelte
<script lang="ts">
  import { setQueryClientContext, createQuery } from '@tanstack/svelte-query';
  import { getQueryClient } from '../lib/queryClient';
  import { QUERY_KEYS } from '../lib/queryKeys';

  // Must be called before any createQuery
  setQueryClientContext(getQueryClient());

  // TanStack Query v6: options wrapped in an accessor function
  const myQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: fetchAllData,
    staleTime: 15_000,
  }));
</script>

<!-- Access results directly — no $ prefix (not a Svelte store) -->
{#if myQuery.isPending}
  <p>Loading…</p>
{:else if myQuery.isError}
  <p>Error: {myQuery.error.message}</p>
{:else}
  <p>{myQuery.data?.someField}</p>
{/if}
```

> **Important:** TanStack Svelte Query v6 returns a reactive **Proxy**, not a Svelte store. Access result properties as `query.data`, `query.isPending`, etc. — **never** with a `$` prefix.

#### Dashboard queries with meta.json polling

Use `useDashboardWithPolling()` from `web/src/lib/useDashboard.svelte.ts` for any island that displays dashboard data. It encapsulates:

- A lightweight sentinel query that polls `meta.json` every 3 minutes (`staleTime: 0`)
- The main dashboard query (no self-polling) that is automatically invalidated when `generated_at` changes

```svelte
<script lang="ts">
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';

  // Internally calls setQueryClientContext — no need to do it separately
  const dashboard = useDashboardWithPolling();

  let field = $derived(dashboard.data?.field ?? initialField);
</script>
```

Because all islands share the same singleton `QueryClient`, only one polling interval runs per page regardless of how many islands call `useDashboardWithPolling()`.

#### Centralized query keys

All query keys are defined in `web/src/lib/queryKeys.ts`:

```ts
QUERY_KEYS.dashboard        // ['dashboard']
QUERY_KEYS.dashboardMeta    // ['dashboard', 'meta']
QUERY_KEYS.iaCoverage(year) // ['ia-coverage', year]
QUERY_KEYS.djenSearch(q)    // ['djen-search', q]
QUERY_KEYS.pipelineRuns     // ['pipeline', 'runs']
QUERY_KEYS.pipelineToday    // ['pipeline', 'today']
```

Use these constants everywhere — never write query key arrays inline in components.

#### Force refresh

When the user triggers a manual refresh, invalidate the relevant query key:

```ts
import { useQueryClient } from '@tanstack/svelte-query';
import { QUERY_KEYS } from '../lib/queryKeys';

const queryClient = useQueryClient();
function handleRefresh() {
  queryClient.invalidateQueries({ queryKey: QUERY_KEYS.iaCoverage(year) });
}
```

Use a plain `writable` store (not TanStack Query) only when the data is entirely local to one island and never fetched from a network endpoint.

### Anti-patterns — State

- **Do not** pass state between islands via Astro props after the page loads. Props are static; they cannot react to changes. Use a store.
- **Do not** store fetched data in a plain module-level `let` variable. It will not be reactive. Use a store.
- **Do not** use `localStorage` as the primary state mechanism. Use a store and persist to `localStorage` only for user preferences (theme, etc.) that need to survive page reloads.

---

## URL State and Routing

URL stability is a first-class concern in this project (Design Constitution principle 8: "Prefer permanence over novelty. Stable URLs"). Every navigable state must be expressible as a URL.

### Query-string state

All search filter state is managed through `web/src/lib/searchQueryString.ts`. The library provides:
- `queryToSearchParams(q)` — converts a typed filter object to `URLSearchParams`
- `searchParamsToQuery(sp)` — parses `URLSearchParams` back to a typed filter object
- `pushQueryToUrl(q)` — writes filter state to the URL via `replaceState` (no history entry)
- `hasAnyQueryValue(q)` — returns `true` if any meaningful filter is set
- `smartParseInput(text)` — detects CNJ process numbers and OAB codes from free text

```ts
import { pushQueryToUrl, searchParamsToQuery } from '../lib/searchQueryString';

// On mount: restore state from URL
const sp = new URLSearchParams(window.location.search);
filters = searchParamsToQuery(sp);

// After a successful search: write state to URL
pushQueryToUrl(effectiveQuery);
```

Use `replaceState` (which `pushQueryToUrl` does internally) for filter changes — no history clutter. Only use history push when a navigation should create a back-button entry.

Do not duplicate the OAB / CNJ regex logic — reuse `smartParseInput()`.

### Hash-based navigation

Use the URL hash for inline drill-down state within a single page (see `TribunalDetail.svelte` and `DateDetail.svelte`). The canonical format is `#YYYY-MM-DD/pg/2/seq/1050` with named key segments. Assignment to `location.hash` creates a history entry (back-button works). `replaceState` does not.

Always listen to both `hashchange` and `popstate` for full back-button support:

```ts
onMount(() => {
  hashState = parseHash();
  const onNavigate = () => { hashState = parseHash(); };
  window.addEventListener('hashchange', onNavigate);
  window.addEventListener('popstate', onNavigate);
  return () => {
    window.removeEventListener('hashchange', onNavigate);
    window.removeEventListener('popstate', onNavigate);
  };
});
```

### Dynamic routes (Astro SSG)

Because this is a static site, all dynamic routes must pre-generate every path with `getStaticPaths()`. There is no server fallback:

```ts
// web/src/pages/publicacoes/[tribunal].astro
export function getStaticPaths() {
  return TRIBUNAIS.map(t => ({
    params: { tribunal: t.toLowerCase() }, // URL is lowercase
    props: { tribunalCode: t },             // component receives uppercase
  }));
}
```

### Anti-patterns — URL

- **Do not** sync ephemeral UI state to the URL (accordion state, hover state). Only sync state the user would want to bookmark or share.
- **Do not** call `pushQueryToUrl` on every keystroke — debounce (400 ms), then push after successful search.
- **Do not** create history entries for filter changes — `replaceState` only.
- **Do not** hardcode `/causaganha/` prefix — use `import.meta.env.BASE_URL`.
- **Do not** duplicate CNJ or OAB parsing logic — reuse `smartParseInput()`.

---

## Data Fetching

All data fetching goes through `web/src/lib/fetchData.ts`, which implements retry logic and error handling. Do not call `fetch()` directly in components.

The file exports:
- `fetchWithRetry(url)` — single URL fetch with exponential-backoff retry
- `fetchAllData()` — fetches the full derived dataset. **This is the canonical list of inputs that feed `DerivedData`** and is used as the TanStack Query `queryFn` for `QUERY_KEYS.dashboard`. Any build-time seed assembled in an Astro page must pass the same inputs in the same order, or the seed shape will silently drift from the runtime shape.
- `deriveData(stats, dashboardData, cacheData, tribunalStartDates?, tribunalQualityScores?, perfMetrics?, iaSnapshot?)` — pure transformation that merges multiple data sources into the `DerivedData` shape; used in Astro pages at build time

### Build-time hydration: a single source of truth

The build-time seed pattern (Tier 0 under [Four tiers of state](#four-tiers-of-state)) currently has no central helper — every Astro page reimplements its own `readJson()` boilerplate and hand-assembles the arguments to `deriveData()`. This is fragile. The target is a single `loadBuildTimeData()` helper that mirrors `fetchAllData()` but uses `readJson()` synchronously and returns `DerivedData`. Pages would then call `loadBuildTimeData()` once and pass slices of its result as `initialXxx` props. Until that helper exists, align any new page with `fetchAllData()`'s input list exactly.

**The helper must live in a server-only module — not in `fetchData.ts`.** `fetchData.ts` is imported by client code (TanStack Query `queryFn`s and many `.svelte` components via `fetchWithRetry`), so any `readJson()` call added there would transitively pull `node:fs` / `node:path` into the browser bundle. Create a dedicated file such as `web/src/lib/buildTimeData.ts` that imports `readJson` and `deriveData`, and document in a file-top comment that **it must only be imported from `.astro` frontmatter** (never from `.svelte`, never from a `.svelte.ts` store, never from anything reachable by client code).

```ts
// Correct — use the exported helpers
import { fetchWithRetry } from '../lib/fetchData';
const result = await fetchWithRetry('/api/julgamentos');

// Wrong — bypasses retry logic and error handling
const result = await fetch('/api/julgamentos').then(r => r.json());
```

Pair every fetch with a Zod schema parse so that bad data surfaces immediately as a validation error rather than silently corrupting the UI.

---

## Loading, Error, and Empty States

Three reusable components handle these states. Use them consistently — do not invent new patterns per component.

| State | In `.astro` pages/layouts | In `.svelte` islands |
|---|---|---|
| No content | `<EmptyState title="..." message="..." />` | Inline `<div class="empty-state">` markup |
| Error | `<AlertBanner level="error" ... />` | Inline `<div class="alert alert-error" role="alert">` markup |
| Loading | Skeleton shimmer (see `web/SKELETON_LOADERS.md`) | Same — `<div class="skeleton skeleton-card">` |

### Three-state template

The canonical pattern for any island that fetches data:

> **Important:** `EmptyState.astro` and `AlertBanner.astro` are Astro components — they cannot be imported or rendered inside `.svelte` files. Use inline markup in Svelte islands. These Astro components are for use in `.astro` pages and layouts only.

```svelte
{#if $store.loading && !$store.data}
  <!-- Skeleton — mirror the shape of the loaded content, not a generic spinner -->
  <div class="skeleton skeleton-card"></div>
{:else if $store.error}
  <div class="alert alert-error" role="alert">
    <strong>Erro ao carregar dados:</strong> {$store.error}
  </div>
{:else if !$store.data || Object.keys($store.data).length === 0}
  <div class="empty-state">
    <p>Nenhum resultado encontrado.</p>
  </div>
{:else}
  <!-- Happy path -->
{/if}
```

### Multi-stage loading

For complex initialisation flows (such as DuckDB), use a typed status enum instead of separate boolean flags:

```ts
type Status = 'loading-db' | 'loading-data' | 'ready' | 'error';
let status = $state<Status>('loading-db');
```

This prevents invalid combinations (`loading: true` and `error` both truthy) and makes control flow explicit.

### Error recovery

Always provide a retry path for transient failures:

```svelte
{#if status === 'error'}
  <div class="error-card">
    <p>{errorMsg}</p>
    <button onclick={() => { status = 'loading-db'; init(); }}>Tentar novamente</button>
  </div>
{/if}
```

### Anti-patterns — States

- **Do not** show plain "Loading..." text for content that takes longer than ~200 ms. Use a skeleton that mirrors the loaded shape.
- **Do not** swallow errors silently. Capture and display every failure.
- **Do not** show `EmptyState` while data is still loading — check `loading` first.
- **Do not** omit retry buttons on transient network failures.
- **Do not** show the skeleton again once data has loaded, even during a background refresh — keep the stale data visible and refresh it in place.

---

## DuckDB WASM

DuckDB runs entirely in the browser via WASM. It is used for the SQL explorer interface and for client-side analytical queries over downloaded datasets.

Because DuckDB requires the browser environment, any component that uses it must be a Svelte island with `client:only="svelte"`. There is no server-side counterpart.

Keep DuckDB initialization in a single place. The singleton is implemented at `web/src/lib/duckdbSingleton.ts`. Import `getDuckDB()` from there — never call DuckDB init directly:

```ts
import { getDuckDB } from '../lib/duckdbSingleton';

const { db, conn } = await getDuckDB(); // lazy, shared, safe to call multiple times
```

The singleton uses double-checked locking with an `initializationPromise` to prevent concurrent initialization. It also configures the httpfs extension for querying Parquet files hosted on the Internet Archive.

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
- Use `interface` for things that may be extended (component prop shapes — including `$props()` declarations — that other code might augment).
- Never use `any`. Use `unknown` when the type is genuinely unknown and then narrow it.
- Do not use non-null assertion (`!`) except where the value is structurally guaranteed (e.g., immediately after a null-check guard at the top of a function).

**Exception — data-layer boundary types:** `DerivedData` in `fetchData.ts` and the store state shape currently use `any` because data originates from heterogeneous JSON sources (Internet Archive, static cache files) whose schemas are not yet fully codified. This is a tracked gap; strict typing will replace them incrementally. Rules for working in this layer:

- Do not spread `any` deeper than the boundary. Use `unknown` + type narrowing inside component and store logic.
- When adding a new field to `DerivedData`, give it the most specific type you can.
- Add a `// TODO: type this` comment on any new `any` field.
- Never use `any` in component `$props()` declarations or in store APIs for data you control.

---

## Known Gaps

These areas are not yet covered by existing infrastructure. Be aware before assuming they exist.

- **No end-to-end tests.** Playwright or a similar e2e framework is not set up. BDD tests run in jsdom only and do not test real browser behavior or full page navigation.
- **No i18n.** All UI strings are hardcoded in Portuguese. There is no translation framework in place.
- **Accessibility.** Guidelines and known gaps are documented in `web/ACCESSIBILITY.md` and `web/ACCESSIBILITY_IMPROVEMENTS_NEEDED.md`. Read both before modifying any UI component — do not introduce new accessibility regressions.
- **Build-time hydration has no central source of truth.** Every Astro page that seeds a Svelte island reimplements its own `readJson()` + `deriveData()` boilerplate, and pages read different subsets of the underlying JSON files. This means the build-time seed shape silently differs from the `fetchAllData()` runtime shape on any page that forgets a source. The fix is a single `loadBuildTimeData()` helper in a dedicated **server-only** module (e.g. `web/src/lib/buildTimeData.ts`) — **not** in `fetchData.ts`, which is imported by client code and would leak `node:fs` into the browser bundle (see [Data Fetching](#data-fetching)). Until it lands, always pass `deriveData()` the exact same arguments that `fetchAllData()` does.
- **`DerivedData` is mostly `any`.** See the [TypeScript](#typescript) section's carve-out. Strict typing will be added incrementally as schemas are codified.

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

---

## Design Constitution

The philosophy every frontend decision serves. Referenced throughout this guide.

### Principles

**1. Build for readers, not for impressions.**
The page exists to help someone think, find, compare, and return.
Not to look "modern," not to maximize time-on-site, not to feel like a product demo.

**2. Content is the interface.**
Do not treat text as filler between visual elements.
The words, headings, links, footnotes, tables, and structure *are* the design.

**3. Density is good when structure is strong.**
Do not fear information-rich pages. Fear disorganized pages.
A dense page with hierarchy is often better than a sparse page with hidden content.

**4. Legibility beats style.**
Readable text, stable rhythm, good line length, sane contrast, clear headings.
If a visual choice hurts reading, it loses.

**5. Speed is part of aesthetics.**
Fast pages feel intelligent. Slow pages feel sloppy.
Performance is not technical polish; it is user respect.

**6. HTML first, CSS second, JavaScript last.**
Start from a document that works without scripting.
Then enhance.
This usually leads to better reliability, accessibility, and longevity.

**7. Make links do real work.**
A good site is not just pages; it is a web of relations.
Use links to define context, provenance, related ideas, objections, updates, and further reading.

**8. Prefer permanence over novelty.**
Stable URLs, durable formatting, timeless layouts, archives that remain usable.
A site should age like a library, not like a startup landing page.

**9. Expose structure instead of hiding it.**
Show dates, categories, references, tags, versions, notes, update history when useful.
Users should feel the underlying order.

**10. User control matters.**
No surprise autoplay, no hostile popups, no scroll hijacking, no trapped text, no broken back button, no "appifying" what should be a page.

**11. Every visual choice must earn its place.**
Decoration is allowed. Waste is not.
Ask of every element: does this clarify, orient, emphasize, or delight enough to justify itself?

**12. Treat search, navigation, and discoverability as first-class.**
A beautiful archive that cannot be explored is a failed archive.

**13. Design for revisiting.**
Most valuable sites are not consumed once.
Make them easy to bookmark, skim, search, annotate mentally, and come back to later.

**14. Respect the reader's cognition.**
Do not fragment attention with too many moving parts.
Use whitespace, headings, sidenotes, lists, summaries, and visual anchors to reduce mental load.

**15. Seriousness is a style.**
A site can feel calm, trustworthy, and intelligent without looking corporate or sterile.
Clarity itself creates authority.

### Practical defaults

If you want these principles to become concrete habits:

**Use a single-column reading layout by default.**
Add side material only when it truly helps.

**Let pages get long.**
Scrolling is cheap; confusion is expensive.

**Use headings aggressively.**
A reader should understand the page's shape in seconds.

**Prefer inline explanation over hidden interaction.**
Do not force users to click six times to see what could simply be on the page.

**Use typography, not gimmicks, for hierarchy.**
Size, weight, spacing, indentation, rules, notes.

**Keep navigation stable across the site.**
Consistency reduces friction more than cleverness creates delight.

**Use images sparingly and purposefully.**
An image should explain, document, or create mood. Not just decorate emptiness.

**Make citations, references, and outbound links easy to inspect.**
Show that claims connect to sources.

**Write meaningful link text.**
Not "click here," but what the reader will actually get.

**Design pages as durable documents.**
Someone opening the page two years later should still understand it.

### What to avoid

Avoid these unless you have a very good reason:

* hero sections that push content below the fold
* oversized typography that reduces information throughput
* carousels
* heavy animation
* full-page loaders
* ambiguous navigation labels
* excessive cardification of everything
* infinite scroll for archival content
* hiding useful metadata
* forcing app patterns onto simple reading tasks

### A compact manifesto

If you want the short version:

**Make pages that are fast, readable, dense, link-rich, stable, and respectful.
Let content dominate, let structure be visible, and let users stay in control.**

### If you want a Gwern-adjacent bias specifically

Then add these extra rules:

- **Prefer knowledge architecture over visual branding.**
- **Reward curiosity with depth.**
- **Make context cheap to access.**
- **Assume the reader is intelligent.**
- **Optimize for long-term usefulness, not first-glance wow.**

### Build checklist

Use these 7 tests for evaluating new pages or components:

- [ ] Can the page be understood in 10 seconds?
- [ ] Can it be read comfortably for 10 minutes?
- [ ] Can it be searched, linked, and revisited easily?
- [ ] Does it work without JavaScript?
- [ ] Is every major claim or section connected to context?
- [ ] Does the layout help information density without feeling chaotic?
- [ ] Would this still feel good in five years?
