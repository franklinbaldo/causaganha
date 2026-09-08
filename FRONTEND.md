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
| Styling | Panda CSS (`cobogo` preset — tokens, recipes) + Vanilla CSS in `index.css` for three legacy Svelte islands |
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
- Interactivity is **light DOM manipulation** that a plain `<script>` tag handles easily (example: `NetworkStatusBanner.astro` listens for `cg-network-*` custom events with `addEventListener` and toggles `hidden` on plain DOM nodes, without any Svelte overhead).
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
| Core data fetching | `fetchData.ts`, `readJson.ts`, `duckdbSingleton.ts` |
| TanStack Query / async state | `queryClient.ts`, `queryKeys.ts` |
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

**0. Build-time static seed** — Astro pages run at **build time** (not at request time, because this site is static). Each page loads the data it needs in its own frontmatter via `loadContract()` (query contracts, see CLAUDE.md's "Manifest query contracts") and/or `readJson()` for standalone static JSON, then passes specific fields as typed `initialXxx` props to Svelte islands:

```astro
---
// web/src/pages/publicacoes/[tribunal].astro (runs at BUILD TIME)
import { loadContract } from '../../lib/data';
import { readJson } from '../../lib/readJson';

const coverageRow = ((await loadContract('tribunal_coverage')) ?? [])
  .find(row => row.tribunal.toUpperCase() === tribunalUpper);
const tribunalStartDates = readJson<Record<string, string>>('tribunal_start_dates.json') ?? {};
---
<TribunalDetail
  client:only="svelte"
  tribunalCode={tribunalCode}
  initialUploadedDates={uploadedDates}
  initialStartDate={tribunalStartDates[tribunalUpper] ?? null}
/>
```

```svelte
<!-- web/src/components/TribunalDetail.svelte (runs in the BROWSER) -->
<script lang="ts">
  let { initialUploadedDates, initialStartDate }: TribunalDetailProps = $props();

  // The island renders directly from the build-time seed — there is no
  // client-side live-refresh layer for this tier today.
  let coverageSet = $derived(new Set(initialUploadedDates));
</script>
```

Always pass build-time data as `initialXxx` props when the page has it. Never leave an island with `null` initial state when the page can pre-populate it — the skeleton flash is user-visible and avoidable. Islands that do need live, post-load data use TanStack Query directly for that one query (see below) rather than a shared dashboard-wide refresh helper — no such helper currently exists in this codebase.

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

The `--cg-*`/`--papel-*`/`--s-*` CSS custom properties (defined in `web/src/index.css`, see "`index.css` — the Legacy-Svelte-Island CSS Bridge" below) are available to any Svelte component's scoped `<style>` block — use them there, do not hardcode colors or spacing values. New Svelte components should still prefer Panda recipes for anything a recipe already expresses (see "Panda's `include` boundary" below for why raw `css({...})` doesn't work inside `.svelte` files).

### Anti-patterns — Svelte

- **Do not** use `$effect` to derive computed values — use `$derived` for that. `$effect` is for side effects only (logging, DOM manipulation, external subscriptions).
- **Do not** write to a `$state` variable inside the `$derived` that reads it. That creates a cycle.
- **Do not** store mutable class instances in `$state` if you want fine-grained reactivity. Svelte tracks object identity, not deep mutations. Use plain objects or arrays.
- **Do not** create stores inside components. Stores belong in `lib/`. A store created inside a component is re-created on every mount.
- **Do not** reach for `onMount` just to set initial state — use `$state` initialization or `$derived` instead.
- **Do not** use a `.svelte.ts` file extension unless you actually need module-level runes. Plain logic belongs in `.ts`.

---

## Panda CSS — Tokens and Recipes as the First Styling Layer

Panda CSS, configured through the shared `cobogo` preset (`web/panda.config.ts`), is the visual baseline for every `.astro` file. `cobogo` sets `globalCss` only for `html`, `body`, `::selection`, and `a` — there is no Pico-style automatic styling of `<button>`, `<table>`, `<article>`, or any other element. Every visual choice beyond that global reset is an explicit call:

1. Reach for a **recipe** (`button`, `card`, `badge`, `alert`, `input`, `article`, `table`, `navLink`) when the element matches one of `cobogo`'s named patterns.
2. Reach for **`css({...})`** for one-off utility styling using the preset's tokens (spacing, color, typography).
3. Add a scoped `<style>` block only for what neither expresses idiomatically.

```astro
---
import { css } from '../../styled-system/css';
import { badge, card, alert } from '../../styled-system/recipes';
---
<span class={badge({ tone: 'info' })}>Cobertura · DJEN</span>

<article class={card({ tone: 'muted' })}>
  <p class={css({ textStyle: 'eyebrow', mb: '4' })}>Média diária</p>
  <strong class={css({ display: 'block', fontSize: '2xl' })}>{avgCoverage30Pct.toFixed(1)}%</strong>
</article>

<div class={alert({ tone: 'attention' })}>
  <strong>Dados de cobertura indisponíveis.</strong>
  <span>O contrato `tribunal_coverage` não foi renderizado neste build.</span>
</div>
```

(Real call sites: `web/src/pages/stats.astro`, `web/src/pages/agentes.astro`, `web/src/layouts/Layout.astro`.)

### Recipes and their variants

Each recipe's variant options live in `node_modules/cobogo/preset/index.mjs` — check there before inventing a one-off style for something a recipe already expresses:

| Recipe | Variants | Real usage |
|---|---|---|
| `button({ visual, size })` | `visual`: `solid` \| `outline` \| `light` \| `dark`; `size`: `sm` \| `md` | `<a class={button({ visual: 'solid' })} href={...}>Consultar processo</a>` (`index.astro`) |
| `card({ tone, lift })` | `tone`: `plain` \| `muted` \| `dark` \| `attention`; `lift`: `flat` \| `raised` | `<article class={card()}>` (`stats.astro`) |
| `badge({ tone })` | `tone`: `neutral` \| `info` \| `attention` \| `accent` | `<span class={badge({ tone: 'info' })}>Projeto & dados</span>` (`sobre.astro`) |
| `alert({ tone })` | `tone`: `info` \| `attention` \| `success` | `<div class={alert({ tone: 'info' })}>` (`explorador.astro`, `processo.astro`) |
| `input({ density })` | `density`: `compact` \| `comfortable` | form inputs across search islands |
| `article({ density })` | `density`: `editorial` \| `compact` | long-form prose blocks |
| `table({ density })` | `density`: `compact` \| `comfortable` | `<table class={table({ density: 'compact' })}>` (`stats.astro`) |
| `navLink({ active })` | `active`: `true` | `<a class={navLink({ active: pathname.includes(link.match) })}>` (`Layout.astro`) |

### `css()` tokens

`css({...})` (from `styled-system/css`) accepts the preset's semantic tokens directly — `color: 'text'`, `background: 'surfaceMuted'`, `textStyle: 'title'`, spacing scale keys (`p: '6'`, `gap: '4'`), and responsive objects (`fontSize: { base: '2xl', md: '3xl' }`). See `web/src/pages/stats.astro` for dense, real examples of every one of these.

### Semantic HTML — accessibility patterns

These patterns are independent of the styling system (they were true under Pico and remain true under Panda) and are actively followed in this codebase's search UIs (`SearchFilters.svelte`, `SmartSearchInput.svelte`, `IASearchBar.svelte`). Element choice affects assistive-technology behavior regardless of which CSS system renders it:

| Pattern | Correct | Wrong |
|---|---|---|
| Grouped radio / checkbox inputs | `<fieldset><legend>Label</legend>` | `<div><small>Label</small>` |
| Search form | `<form role="search">` | A plain `<div>` wrapper with no search semantics |
| Keyboard-shortcut hint | `<kbd>` outside the `<label>`, wrapped in `aria-hidden="true"` | `<kbd>` inside the `<label>` (pollutes the input's accessible name) |
| Site navigation landmark | `<nav>` for menus/breadcrumbs/pagination | `<nav>` for a cluster of action buttons (use `<div role="toolbar" aria-label="...">` instead) |

```svelte
<!-- Correct — web/src/components/SmartSearchInput.svelte -->
<form role="search">
  <label for="publication-smart-search">Buscar publicações</label>
  <input id="publication-smart-search" type="search" />
  <span class="smart-search__shortcut" aria-hidden="true"><kbd>Ctrl</kbd><kbd>K</kbd></span>
</form>

<!-- Wrong — "Buscar publicações Control K" becomes the field's accessible name -->
<label>
  <input type="search" aria-label="Buscar publicações" />
  <kbd>Ctrl</kbd><kbd>K</kbd>
</label>
```

### Panda's `include` boundary

Panda's `include` in `panda.config.ts` only scans `.astro`/`.js`/`.jsx`/`.ts`/`.tsx` files — **never `.svelte`.** A `css({...})` call written inside a `.svelte` file is unreliable, because any property/value combination not *also* used in an included file never gets its atomic class extracted into the stylesheet (see CLAUDE.md's "CSS token boundary" section for the full explanation and the three legacy Svelte islands this affects). Recipes are safe to call from a Svelte component — their full variant CSS is generated regardless of call site — but raw `css({...})` is not. This is why every Svelte component, new or legacy, styles through global element-level CSS/utility classes (`index.css`) and its own scoped `<style>` block rather than importing `css()` directly.

### Anti-patterns — Panda CSS

- **Do not** write inline `style="background: #1A6B3C; ..."` for anything a token or recipe already expresses. Inline styles ignore theme tokens and can't be overridden.
- **Do not** invent a bespoke CSS class for a button/card/badge/alert/input/article/table/nav-link — check the recipe's variant list first.
- **Do not** call raw `css({...})` from inside a `.svelte` file — see "Panda's `include` boundary" above.
- **Do not** add new custom properties outside `panda.config.ts`/the `cobogo` preset. `web/src/index.css` is a compatibility bridge for three legacy Svelte islands, not a second token system (see CLAUDE.md).

---

## `index.css` — the Legacy-Svelte-Island CSS Bridge

`web/src/index.css` is **not** the primary token system — see "Panda CSS" above for that. It exists only as a compatibility bridge for the three legacy Svelte islands that predate the Panda/`cobogo` reboot and haven't been converted to `css()`/recipes yet (`ProcessoLookup.svelte`, `PublicationSearch.svelte`, `SavedConsultations.svelte`), per CLAUDE.md's "CSS token boundary" section. It defines `--cg-*` primitives backed by Panda's own `--colors-*` custom properties, and re-exposes legacy names (`--papel-*`, `--s-*`, `--color-*`) as aliases to those same values.

### Use tokens — never hardcode

```css
/* Correct — inside one of the three legacy islands' scoped <style> block */
.card {
  padding: var(--s-4);
  background: var(--color-surface);
  color: var(--cg-text);
}

/* Wrong */
.card {
  padding: 16px;
  background: #fffdf8;
  color: #1a1a2e;
}
```

New Svelte components should not introduce new `--cg-*`/`--papel-*`/`--s-*` names — that vocabulary is frozen for the three legacy islands. A new component styles through recipes plus its own scoped `<style>` with literal values, per CLAUDE.md.

### No light/dark theme toggle

CausaGanha is intentionally single-theme (issue #1178): the `cobogo` preset defines one flat palette with no dark-mode variant, no `data-theme` awareness, and no theme-toggle component. `web/src/lib/themeSingleModeGuard.test.ts` is a regression test that fails if any source file reintroduces `data-theme`, `causaganha-theme`, or other pre-#1178 theming markers — do not add a light/dark toggle without first revisiting that decision.

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

- **Do not** write inline `style="..."` with hardcoded values. Use Panda tokens/recipes (`.astro`) or the legacy `--cg-*`/`--papel-*`/`--s-*` aliases (the three legacy Svelte islands only).
- **Do not** use `!important`. If specificity is a problem, restructure the selectors.
- **Do not** add a new one-off color value. Extend the `cobogo` preset (`node_modules/cobogo/preset/index.mjs` is vendored from the `cobogo` package — propose the addition upstream) if a new semantic color is genuinely needed; do not add a new custom property to `index.css`.
- **Do not** duplicate token values by copy-pasting hex codes. Always reference the token or variable.
- **Do not** reintroduce `data-theme` or a light/dark toggle — see "No light/dark theme toggle" above.

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
    queryKey: QUERY_KEYS.iaCoverage(year),
    queryFn: () => fetchAllTribunalMetadata(year, undefined, { useCache: false }),
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

#### Centralized query keys

All query keys are defined in `web/src/lib/queryKeys.ts`:

```ts
QUERY_KEYS.iaCoverage(year) // ['ia-coverage', year]
QUERY_KEYS.djenSearch(q)    // ['djen-search', q]
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

Client-side HTTP calls go through `web/src/lib/fetchData.ts`'s `fetchWithRetry(url)` — a single URL fetch with exponential-backoff retry and error handling. Do not call `fetch()` directly in components.

Build-time data loading is a separate concern (Tier 0 under [Four tiers of state](#four-tiers-of-state)): each Astro page loads what it needs directly in its frontmatter via `loadContract()` (query contracts, see CLAUDE.md) and/or `readJson()` for standalone static JSON, then passes the fields it needs as `initialXxx` props. There is no shared build-time aggregation helper — `loadContract`/`readJson` calls belong in `.astro` frontmatter only, never in `fetchData.ts` or any module reachable from client code, since both use `node:fs` under the hood and would break the browser bundle if pulled in there.

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

**Exception — data-layer boundary types:** some store state shapes (e.g. `workflowStatusStore.ts`'s parsed GitHub API response) currently use `any` because data originates from heterogeneous JSON sources whose schemas are not yet fully codified. This is a tracked gap; strict typing will replace it incrementally. Rules for working in this layer:

- Do not spread `any` deeper than the boundary. Use `unknown` + type narrowing inside component and store logic.
- Add a `// TODO: type this` comment on any new `any` field.
- Never use `any` in component `$props()` declarations or in store APIs for data you control.

---

## Known Gaps

These areas are not yet covered by existing infrastructure. Be aware before assuming they exist.

- **No end-to-end tests.** Playwright or a similar e2e framework is not set up. BDD tests run in jsdom only and do not test real browser behavior or full page navigation.
- **No i18n.** All UI strings are hardcoded in Portuguese. There is no translation framework in place.
- **Accessibility.** Guidelines and known gaps are documented in `web/ACCESSIBILITY.md` and `web/ACCESSIBILITY_IMPROVEMENTS_NEEDED.md`. Read both before modifying any UI component — do not introduce new accessibility regressions.
- **Build-time hydration has no central source of truth.** Every Astro page that seeds a Svelte island calls `loadContract()`/`readJson()` directly and reads different subsets of the underlying data. There is no shared helper enforcing that a page's build-time seed and any later live query stay in sync — check the target island's own props when adding a new data source.

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
