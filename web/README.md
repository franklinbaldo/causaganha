# CausaGanha — Frontend

Static site for the [CausaGanha](https://github.com/franklinbaldo/causaganha) judicial data platform. Tracks the collection and archiving of Brazilian DJEN (Diário de Justiça Eletrônico Nacional) publications across 96 courts.

Deployed to **GitHub Pages** at `/causaganha/`. All pages are pre-rendered at build time; no server runtime.

## Design System

**Brazilian Modernist** — inspired by Athos Bulcão's geometric tiles and Brazilian editorial typography.

| Token | Value | Usage |
|---|---|---|
| Primary | `#1A6B3C` (forest green) | Links, buttons, accents |
| Accent | `#C5972C` (Brazilian gold) | Highlights, warnings, step borders |
| Background | `#FAFAF5` (warm white) | Page background |
| Surface | `#F2EFE8` (cream) | Cards, sections |
| Content | `#1C1C1C` (near-black) | Body text |
| Serif font | DM Serif Display | h1, h2 headings |
| Sans font | Inter | Body text, UI elements |
| Mono font | JetBrains Mono | Code, stats, numbers |

Buttons and search fields use pill shapes (`border-radius: 2rem`). Dark theme uses deep forest green tones (`#0F1A14` base).

All tokens are CSS custom properties defined in `src/index.css`.

## Stack

| Layer | Technology |
|---|---|
| Meta-framework | [Astro 5](https://astro.build) (SSG, `output: static`) |
| Components | [Svelte 5](https://svelte.dev) (runes mode) with `client:*` islands |
| Data fetching | [TanStack Query](https://tanstack.com/query) (`@tanstack/svelte-query@6`) |
| In-browser SQL | [DuckDB WASM](https://duckdb.org/docs/api/wasm/overview) |
| API client | [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) with generated types (`djen.yml`) |
| Charts | [Observable Plot](https://observablehq.com/plot/) |
| Validation | [Zod](https://zod.dev) |
| Sanitization | [DOMPurify](https://github.com/cure53/DOMPurify) |
| Language | TypeScript (strict) |
| Build | Vite 7 |
| Tests | Vitest + Testing Library + vitest-cucumber (BDD) |
| Lint | ESLint (flat config) |

## Development

```bash
npm install
npm run dev        # http://localhost:4321/causaganha/
npm run typecheck  # astro check (includes Svelte diagnostics)
npm run lint
npm run test
npm run build      # output → dist/
```

## Data fetching architecture

### Build time (Astro SSG)

Astro pages read static JSON files from `public/` at build time via `readJson()` in `src/lib/readJson.ts`. The resulting data is passed to Svelte islands as initial props, so pages render fully without JavaScript.

### Runtime (browser islands)

Each interactive Svelte island uses [TanStack Query](https://tanstack.com/query) to stay fresh after initial load.

**Key files:**

| File | Purpose |
|---|---|
| `src/lib/queryClient.ts` | Singleton `QueryClient` shared across all islands on a page |
| `src/lib/queryKeys.ts` | Centralized query key registry |
| `src/components/QueryProvider.svelte` | Sets context + renders DevTools in dev mode |
| `src/lib/useDashboard.svelte.ts` | Dashboard query with meta.json change detection (3-min polling) |

**Data sources:**

- **Internet Archive** (`archive.org/download/causaganha-dashboard/`) — live cache files (`today.json`, `calendar.json`, `runs.json`, `backfill.json`, `ia-snapshot.json`). Fetched client-side with fallback to bundled static files.
- **DJEN API** (`comunicaapi.pje.jus.br`) — live publication search via `src/lib/djenClient.ts`. Geo-fence aware: routes through a Cloud Run proxy when direct access is blocked.
- **Static files** (`public/`) — `run-stats.json`, `dashboard-data.json`, tribunal metadata. Embedded at build time and always available.

**Polling strategy:**

A lightweight sentinel query fetches `meta.json` every 3 minutes. When `generated_at` changes, it invalidates the dashboard query — so a full re-fetch only happens when new pipeline data actually exists.

**Astro islands + TanStack context:**

Because each `client:*` island is an isolated Svelte component tree, calling `setQueryClientContext(getQueryClient())` in the island's script block (before any `createQuery` calls) sets context for that island and all its descendants. The singleton `QueryClient` ensures all islands share the same cache.

## API client

The DJEN API client is generated from `../djen.yml`:

```bash
npm run codegen:djen   # regenerates src/lib/djen-types.gen.ts
```

This runs automatically before `build`, `test`, and `typecheck`.

## Testing

Tests use BDD-style `.feature` files in `src/components/__steps__/`. Each step file imports from `shared.ts` which mocks `queryClient` (fresh `QueryClient` per test) and `fetchAllData` (returns `null`, so components render with their `initialXxx` props).

```bash
npm run test          # single run
npm run test:watch    # watch mode
```

## Project layout

```
web/
├── src/
│   ├── pages/          # Astro routes (SSG)
│   ├── components/     # Svelte + Astro components
│   │   └── __steps__/  # BDD test step definitions
│   ├── layouts/        # Page layout templates
│   └── lib/            # Shared utilities, stores, data fetching
│       ├── queryClient.ts
│       ├── queryKeys.ts
│       ├── useDashboard.svelte.ts
│       ├── fetchData.ts        # fetchAllData, fetchWithRetry, deriveData
│       ├── djenClient.ts       # typed DJEN API wrapper
│       ├── iaMetadataFetcher.ts
│       ├── homepage-content.ts # shared constants for homepage + tests
│       └── duckdbSingleton.ts
├── public/
│   ├── cache/          # Live data files (updated by pipeline)
│   └── *.json          # Static build-time data
├── astro.config.mjs
├── svelte.config.js
└── package.json
```
