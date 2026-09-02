# CausaGanha — Visual & Architecture Audit

**Date:** 2026-05-31  
**Scope:** All pages, shared components, and CSS system  
**Method:** Full source read + design reasoning; no live browser (no dev server available)

> [!NOTE]
> **Archived 2026-09-02, per issue #924 §3.3 ("purgar os restos mortais").**
> Historical snapshot, not a live task list. A spot-check of its concrete
> findings against the current codebase found every item already resolved
> — `admin/*` pages and their missing CSS classes no longer exist,
> `TribunalCompareCard`/`AlertBanner`/`StatCard`/`LawyerCard` all already
> match this doc's own suggested fixes — except item 14
> (`404.astro`'s duplicate `<h1>`), which was still live and is fixed in
> the same change that archived this file (see `web/features/not-found.feature`).
> Kept here as a record of that review, not as open work.

---

## Completed Fixes Log

| Fix | Branch / PR | Status |
|-----|-------------|--------|
| Missing `@media (max-width: 979px)` block in layout.css; `--radius-selector` undefined; QueryCard copy-btn icon swap | PR #755 | ✅ merged |
| Priority-1: define `.cg-pulse` animation (base.css); remove duplicate `.sr-only` (data-viz.css); fix AlertBanner role semantics; fix TribunalCalendar hardcoded BASE_URL + hardcoded date; homepage KPI card 3/4 placeholder labels; add "Demonstração" badge to calendar; remove `JulesSessionStatus` (foreign component); fix admin/index broken CSS layout; fix admin breadcrumbs + navigation | PR #755 branch | ✅ committed |
| Remove live-data widgets with no backing data: delete `ActivePipelineStatus.svelte`, `LiveStatusWidget.svelte`, `WorkflowStatusBadge.astro`; remove them from `Header.astro` and `PerfDashboard.svelte`; fix test mock; add "Demonstração" label to index.astro calendar section; fix AlertBanner `isLive` derivation | PR #756 | ✅ open |
| Feature-creep purge: delete all 5 `/admin` pages (unlinked from nav); delete 10 admin-exclusive components + `completedItemsStore`; delete orphaned step tests/features/stubs; surface `ManifestStatus` (live IA coverage) on public `stats.astro`; remove misleading "Ctrl+K" nav hint | `fix/remove-admin-and-feature-creep` | 🔄 this PR |

---

## Evaluation Dimensions

| Symbol | Dimension | What it measures |
|--------|-----------|-----------------|
| **VH** | Visual Hierarchy | Headings, spacing, scanability, information density |
| **DC** | Design Consistency | Correct use of tokens, coherent patterns across the system |
| **RL** | Responsive Layout | Mobile / tablet / desktop behavior, overflow, touch targets |
| **A11y** | Accessibility | ARIA, semantic HTML, focus states, color contrast |
| **DM** | Dark Mode | Complete and correct dark mode implementation |
| **EE** | Empty & Error States | Loading, error, empty data graceful degradation |
| **CA** | Component Architecture | Reusability, composition, prop design, code quality |

**Rating:** ★☆☆☆☆ (broken) → ★★★★★ (excellent)

---

## Pages

---

### 1. `index.astro` — Homepage

> **What it should look like:** A bold editorial landing page. Big typographic hero with a live search bar, 4-column KPI grid, a 12-month tribunal calendar, and a "Why archive" section with a pull quote. Maximum impact in the first viewport.

| Dimension | Rating | Issues dragging the score |
|-----------|--------|--------------------------|
| VH | ★★★★☆ | The third ("Hoje") and fourth ("Lacunas") KPI cards permanently display "—" with no data. Two of four hero stats are broken placeholders. |
| DC | ★★★★☆ | Uses the full Brazilian Modernism system correctly. `style="color: rgba(255,255,255,0.6);"` inline on card sub-text instead of a token. |
| RL | ★★★★☆ | Fixed by PR #755. Previously the `@media (max-width: 979px)` block was missing, so the 2-column grid applied everywhere. |
| A11y | ★★★★☆ | Good aria-labelledby on sections. The hero tile `<div>` is correctly `aria-hidden`. The search chips `<button>` elements have no tooltip/title explaining what clicking them does. |
| DM | ★★★★★ | Comprehensive dark mode with all custom tokens covered. |
| EE | ★★☆☆☆ | "Hoje" and "Lacunas" KPI cards always show `—`. No loading state, no "coming soon" label. Looks like broken data. |
| CA | ★★★☆☆ | Hero tile generation is a 30-line inline `<script>` that could be an Astro component. Search chip JS also inline. |

**Top fix:** Replace the `—` placeholders in KPI cards 3 and 4 with a `<small>data em breve</small>` label or actually wire up real data from the manifest.

---

### 2. `publicacoes/index.astro` — Publications Search

> **What it should look like:** A search-first page. Large editorial header, a warning card about coverage gaps, then the live search interface powered by `PublicationSearch.svelte`.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | The attention card (§ coverage gaps) takes up significant space before the search — always shows as info, even if there are no gaps. Users see a warning before they've done anything. |
| DC | ★★★☆☆ | Mixes `.page-head` / `.wrap` / `.kicker` (Brazilian Modernism tokens) with `section` tags that use inline `style="padding: var(--s-7) 0 var(--s-9);"`. The inline padding should use a CSS class. |
| RL | ★★★★☆ | `wrap--wide` works. `PublicationSearch` handles its own responsive layout. |
| A11y | ★★★★☆ | `aria-label` on sections. The attention card `<article>` inside a `<section aria-label>` is correct. |
| DM | ★★★☆☆ | `.attention-card` uses `color-mix` which adapts, but `var(--color-surface)` resolves differently in dark mode — needs verification. |
| EE | ★★★★☆ | Delegates to `PublicationSearch` which has its own loading/error states. |
| CA | ★★☆☆☆ | The attention card is **hardcoded** with static text about "cobertura e lacunas". It should either be driven by real data (hide when all tribunals are healthy) or removed. Currently always visible regardless of system state. |

---

### 3. `publicacoes/[tribunal].astro` — Tribunal Detail Page

> **What it should look like:** A per-tribunal dashboard. Header with tribunal code, breadcrumbs, then `TribunalDetail.svelte` which shows coverage charts, calendar, attention cards.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | The page `<title>` in the Header is set with an empty string `title=""` and slots the title in via a Fragment — confusing pattern that could easily break. |
| DC | ★★★☆☆ | The OG image generator inside the `.astro` file mixes presentation logic (SVG generation) with routing. The generated SVG uses hardcoded hex colors (`#0f172a`, `#1e293b`) not related to the design system. |
| RL | ★★★★☆ | Delegates to `TribunalDetail.svelte`. |
| A11y | ★★★★☆ | Breadcrumbs with aria-current. Title slot is correctly announced. |
| DM | ★★★☆☆ | The OG image SVG has hardcoded dark colors that don't respond to user theme. |
| EE | ★★★☆☆ | Shows 0 zips gracefully. |
| CA | ★★☆☆☆ | OG image SVG generation at build time is inside the routing `.astro` file. It should be extracted to a utility function or a separate build script. |

---

### 4. `explorador.astro` — SQL Explorer

> **What it should look like:** A focused tool page. Short description of what the explorer does, a usage guide in an article card, then the full DuckDB Explorer component.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | The page title is just `"SQL"` — both in the `<Layout>` title and in the `<Header>`. "SQL" is too terse; "Explorador de Dados" or "Consultas SQL" would be clearer and matches the breadcrumb label. |
| DC | ★★★★☆ | Double-container `class="container"` nesting fixed in PR #755. |
| RL | ★★★★☆ | DuckDB Explorer handles its own layout. |
| A11y | ★★★★☆ | External link to Internet Archive has `rel="noopener noreferrer"`. |
| DM | ★★★☆☆ | `DuckDBExplorer` internal dark mode unknown. |
| EE | ★★★☆☆ | DuckDB WASM load failures handled inside component. |
| CA | ★★★★☆ | Clean page wrapper. |

**Fix:** Change `title="SQL"` to `title="Explorador de Dados"` in both Layout and Header, and update breadcrumb accordingly.

---

### 5. `dados.astro` — Open Data / API Docs

> **What it should look like:** Documentation page. Overview stats, format descriptions with CTA buttons, schema tables in expandable `<details>`, code examples.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Good use of `<details open>` / `<details>` for progressive disclosure of schemas. |
| DC | ★★★★☆ | Mixes `<article>` nesting correctly with Pico. Some indentation inconsistency in the `<details>` table wrappers (extra indentation on `<table>` tag). |
| RL | ★★★★☆ | `table-responsive` wrapper on all tables. `pre/code` blocks may overflow on narrow screens — no `overflow-x: auto` on `pre` globally (Pico adds it but worth verifying). |
| A11y | ★★★★☆ | `<details>` / `<summary>` is keyboard accessible natively. Tables have `<thead>`. |
| DM | ★★★☆☆ | `pre/code` blocks use Pico's dark mode. |
| EE | ★★★★☆ | Handles missing `iaSnapshot` gracefully (omits the stats grid). |
| CA | ★★★★☆ | Static content page. Good structure. |

---

### 6. `stats.astro` — Indicators / Coverage Statistics

> **What it should look like:** A metrics dashboard. Overview KPI figures, two ranking lists (best/worst tribunals), a 7-day-of-week pattern grid.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Uses `<figure>` / `<figcaption>` for stats. `<figure>` is semantically for images/illustrations. Stat cards would be clearer as `<article>` with the established `StatCard` component. The weekly pattern section nests `<article>` inside `<article>`, creating Pico's card-within-card visual. |
| DC | ★★☆☆☆ | Uses `.stat-value` / `.stat-label` from `data-viz.css` on `<figure>` elements, **and** the pre-existing `StatCard` component exists but is not used here. Two systems for displaying stats side-by-side. |
| RL | ★★★★☆ | `auto-grid` responsive. |
| A11y | ★★★☆☆ | `data-tone` on `<div class="stat-value">` does not match the expected element (should be on `<strong>` per `StatCard`). |
| DM | ★★★☆☆ | Relies on Pico + token inheritance. |
| EE | ★★★★☆ | Shows `--` for missing data. Provides zero-data fallbacks. |
| CA | ★★☆☆☆ | Does not reuse `StatCard`. Invents `<figure>` pattern not used elsewhere. |

**Fix:** Replace the `<figure>` elements with `StatCard`, and replace the nested weekly `<article>` pattern with a proper CSS grid of simple stat displays.

---

### 7. `sobre.astro` — About / Methodology

> **What it should look like:** An editorial article. Clean prose with section headings, a list of data access formats, a license note.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Good. Five `<article>` sections with `<h2>` headings. |
| DC | ★★★★☆ | Correct use of Pico article/section nesting. `<section class="container">` used — this applies container padding to a section, which is slightly unusual but visually fine. |
| RL | ★★★★☆ | Container. |
| A11y | ★★★★☆ | Clean semantic HTML. `<kbd>` for inline code. |
| DM | ★★★★☆ | Pico handles prose. |
| EE | N/A | Static content. |
| CA | ★★★★★ | Clean, simple, no complexity. |

---

### 8. `changelog.astro` — Changelog

> **What it should look like:** A reverse-chronological list of entries with dates, headings, and bullet lists.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Only 2 hardcoded entries from April 2026. The most recent entry is from 2 months ago — looks abandoned. The `<small>` tag wrapping the `<time>` makes the date visually too small. |
| DC | ★★★★☆ | Correct Pico article with time element. |
| RL | ★★★★☆ | Container. |
| A11y | ★★★★★ | `<time datetime={entry.date}>` with proper formatting. |
| DM | ★★★★☆ | Pico. |
| EE | N/A | If `entries` array is empty, the section renders nothing — no "no entries yet" message. |
| CA | ★★☆☆☆ | Entries are hardcoded in the `.astro` file. Should be a markdown/JSON data source. |

---

### 9. `dicionario.astro` — Data Dictionary

> **What it should look like:** A reference page. A full table of every field across all Parquet tables, filterable by table name.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★☆☆☆ | Only 6 entries covering 4 of the 10+ tables. The page looks sparse and incomplete. A user who comes here for schema reference will be disappointed. |
| DC | ★★★★☆ | Correct Pico striped table, `table-wrap` for horizontal scroll. |
| RL | ★★★★☆ | `table-wrap`. |
| A11y | ★★★★☆ | `scope="col"` on headers. |
| DM | ★★★★☆ | Pico table dark mode. |
| EE | N/A | Static. |
| CA | ★★☆☆☆ | 6 hardcoded rows when `dados.astro` has 10 tables fully documented. The dictionary is a strict subset of what's already in `dados.astro` and adds no value in its current form. **Candidate for deletion or merge.** |

---

### 10. `comparador.astro` — Tribunal Comparator

> **What it should look like:** A grid of up to 12 tribunal cards sorted by historical coverage span, each with dates and a link to the tribunal's publication page.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | The page header subtitle is "Tribunais com maior cobertura histórica — do mais antigo ao mais recente" but the page title in the Header says "Comparador de Tribunais". No `backHref` goes to the homepage — goes to `publicacoes` instead. |
| DC | ★★★★☆ | `auto-grid` + `TribunalCompareCard`. Double-container fixed in PR #755. |
| RL | ★★★★☆ | `auto-grid` collapses correctly. |
| A11y | ★★★☆☆ | Each card's "Abrir tribunal" link provides insufficient context for screen readers. |
| DM | ★★★☆☆ | Pico article dark mode. |
| EE | ★★★★☆ | `EmptyState` shown when no snapshot available. |
| CA | ★★★★☆ | Good data transformation, clean card delegation. |

---

### 11. `consultas.astro` — Pre-built SQL Queries

> **What it should look like:** A gallery of 3 SQL query cards with copy buttons, linking to the explorer.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Very thin page — 3 cards. No visual indication that queries can be run (no "Open in Explorer" flow at the page level). |
| DC | ★★★★☆ | Uses `QueryCard`. Copy-button SVG swap fixed in PR #755. |
| RL | ★★★☆☆ | `pre/code` inside cards may overflow on mobile — `QueryCard` has no overflow handling on the `pre`. |
| A11y | ★★★★☆ | Copy button has `aria-label`, `aria-live` on status. |
| DM | ★★★☆☆ | Inherits. |
| EE | ★★★★☆ | Fallback to text selection if clipboard API unavailable. |
| CA | ★★★☆☆ | 3 hardcoded queries. Could be a `.qmd`-style data source. No way to filter by table. |

---

### 12. `advogados.astro` — Lawyers / OAB

> **What it should look like:** A page focused on finding lawyers. Stats about coverage, a leaderboard of rated lawyers, a grid of tribunal coverage cards linking to per-tribunal guidance.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★☆☆☆ | Three disconnected sections with no clear user journey: (1) stat summary, (2) leaderboard table, (3) tribunal coverage grid. The leaderboard shows a "(TJRO Sandbox)" note in the heading, making it look experimental. Empty leaderboard state shows "Nenhum advogado atingiu os critérios" — the most common path. |
| DC | ★★☆☆☆ | Heavy use of inline styles (partially cleaned in PR #755). The `<h2>` headings are still structurally inconsistent — one inside an `<article>`, one standalone. |
| RL | ★★★☆☆ | `table-responsive` on leaderboard table. `auto-grid` for tribunal grid. |
| A11y | ★★☆☆☆ | `<progress>` elements in the leaderboard have no accessible label. The win-rate progress bar is purely decorative — the percentage is printed next to it but AT would read `value/100` without context. |
| DM | ★★★☆☆ | Emoji medals (🥇🥈🥉) are not dark-mode-aware (though they're fine visually). |
| EE | ★★★☆☆ | Empty leaderboard state handled. Missing BackFill data shows empty tribunal grid with no message. |
| CA | ★★☆☆☆ | `LawyerCard` has a prop named `index` which receives a stats object — misleading name. Two unrelated features (leaderboard + tribunal coverage) in one page. |

---

### 13. `advogados/[oab].astro` — Lawyer Detail by Tribunal

> **What it should look like:** A detail page for a specific OAB number's activity across tribunals.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★☆☆☆ | The page actually routes by **tribunal code** (e.g., `/advogados/tjsp`), not by OAB number. The URL, file name, and the word "advogados" imply a lawyer lookup but it's a tribunal-scoped SQL template generator. Deeply confusing. |
| DC | ★★★☆☆ | Uses `AlertBanner`, `StatCard`, `EmptyState` correctly. |
| RL | ★★★★☆ | Container. |
| A11y | ★★☆☆☆ | `AlertBanner` uses `role="alert"` (a live region that announces immediately) for informational static content — should be `role="note"` or no role. |
| DM | ★★★☆☆ | Inherits. |
| EE | ★★★★☆ | `EmptyState` shown for unknown tribunal. |
| CA | ★☆☆☆☆ | **Fundamentally misnamed.** `[oab].astro` routes by tribunal code via `getStaticPaths()` which reads `backfill.json` tribunal codes. The file should be `[tribunal].astro` and the route `/advogados/tribunal/tjsp`. The entire `advogados/` sub-section of the site needs rethinking. |

---

### 14. `404.astro` — Not Found

> **What it should look like:** Clear "not found" message with two CTAs: search and home.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Has both a `<h1>` in the page-header (`"Página não encontrada"`) AND a second `<h1 aria-hidden="true">404</h1>` in the content — two h1 elements on the page (even if one is hidden). The hgroup/h1/p structure is redundant when the Header already shows the title. |
| DC | ★★★★☆ | Simple, clean Pico. |
| RL | ★★★★☆ | Container. |
| A11y | ★★☆☆☆ | Two `<h1>` on the same page violates heading structure. The second `<h1>` is `aria-hidden` but the heading structure is still confusing. Should be `<p class="stat-value">404</p>` or `<span>`. |
| DM | ★★★★☆ | Pico. |
| EE | N/A | Is itself the error state. |
| CA | ★★★★☆ | Simple, appropriate. |

---

### 15. `admin/index.astro` — Admin Dashboard

> **What it should look like:** An internal dashboard entry point. A grid of links to sub-pages, plus sidebar widgets for Jules assistant status, audit log, and omission cost.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★☆☆☆☆ | **BROKEN.** Five CSS classes are used (`admin-grid`, `admin-main`, `admin-sidebar`, `pages-grid`, `bottom-section`) with zero definitions anywhere in the codebase. The page renders as a flat vertical stack of unstyled divs. |
| DC | ★☆☆☆☆ | Also uses `admin-page-link` — undefined. No breadcrumbs. No back navigation in Header. |
| RL | ★☆☆☆☆ | No layout because no CSS. |
| A11y | ★★☆☆☆ | `<aside>` for sidebar is correct semantic. But no breadcrumbs, no skip-to-content for admin pages. |
| DM | ★☆☆☆☆ | Unknown, layout is broken. |
| EE | ★★★☆☆ | Sub-components handle their own states. |
| CA | ★★☆☆☆ | Correct component composition conceptually, but the missing CSS makes it non-functional. |

---

### 16. `admin/perf.astro` — Performance Monitoring

> **What it should look like:** A monitoring dashboard. KPI from `PerfDashboard`, then three heatmaps in collapsible `<details>`.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | `<details open>` / `<details>` for heatmaps is a reasonable progressive disclosure. No breadcrumbs. |
| DC | ★★★☆☆ | No back navigation (Header has no `backHref`). |
| RL | ★★★★☆ | Container, heatmaps handle own layout. |
| A11y | ★★☆☆☆ | Missing breadcrumbs and back nav — disorienting within the admin section. |
| DM | ★★★☆☆ | Inherits. |
| EE | ★★★★☆ | `PerfDashboard` handles its own states. |
| CA | ★★★★☆ | Good component composition. |

---

### 17. `admin/backfill.astro` — Manifest Status

> **What it should look like:** A sortable table of all tribunals with upload/coverage metrics, fetched live from Internet Archive.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Fully delegated to `ManifestStatus`. No page-level headings, no breadcrumbs, no context. |
| DC | ★★☆☆☆ | No breadcrumbs, no back navigation. |
| RL | ★★★☆☆ | ManifestStatus table may not have overflow handling. |
| A11y | ★★☆☆☆ | No breadcrumbs for navigation context. |
| DM | ★★★☆☆ | ManifestStatus inherits. |
| EE | ★★★★☆ | ManifestStatus has loading/error states. |
| CA | ★★★★☆ | Single-component page — fine for admin tools. |

---

### 18. `admin/quality.astro` — Data Quality Scores

> **What it should look like:** A tribunal quality ranking. Sortable table or visual scale showing score per tribunal.

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★☆☆☆ | Uses a raw `<dl>` with `<dt>` tribunal / `<dd>` score. No visual treatment — it's a plain text list of `TJSP 0.923`. No progress bars, no color coding, no sort. |
| DC | ★★★☆☆ | Uses `StatCard` for summary. Uses `EmptyState`. But the main content (`<dl>`) has no design system treatment. |
| RL | ★★★★☆ | Container. |
| A11y | ★★★★☆ | `dt`/`dd` used correctly. |
| DM | ★★★☆☆ | Inherits. |
| EE | ★★★★☆ | `EmptyState` for missing data. |
| CA | ★★☆☆☆ | The `<dl>` approach for a score table should be replaced with a proper sortable table or visual component. |

---

## Shared Components

---

### 19. `Layout.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★★ | Sets correct structure. |
| DC | ★★★★★ | Manages CSS imports, Google Fonts, Pico base. |
| RL | ★★★★★ | `fullWidth` prop correctly omits container. |
| A11y | ★★★★★ | Skip link, `lang="pt-BR"`, canonical URL, OG meta, theme-color. |
| DM | ★★★★★ | Inline head script prevents FOUC perfectly. |
| EE | N/A | — |
| CA | ★★★★★ | Minimal, clean. No issues. |

---

### 20. `Header.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Two variants (home/page) working well. Desktop nav links use "Jurisprudência" for `/publicacoes`, which is a mismatch — the page says "Publicações". |
| DC | ★★★★☆ | Uses design tokens throughout. |
| RL | ★★★★★ | `desktop-only`/`mobile-only` breakpoints. Nav drawer for mobile. |
| A11y | ★★★★☆ | Dialog used for mobile drawer with `showModal()`. Focus returned on close. `aria-haspopup`, `aria-controls` present. |
| DM | ★★★★★ | All variants styled for dark mode. |
| EE | ★★★☆☆ | `ActivePipelineStatus` polls but has no `aria-live` region — status changes are invisible to AT. |
| CA | ★★★☆☆ | One component handling two substantially different layouts. The home variant and the page variant share a 300-line file. Could be split into `SiteNav.astro` + `PageHeader.astro`. |

---

### 21. `Footer.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| All | ★★★★★ | Clean, minimal, correct. External link has `aria-label` noting "abre em nova aba". Copyright year is dynamic. |

---

### 22. `Breadcrumbs.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| All | ★★★★★ | Correct semantic `<nav>`, `aria-label`, `aria-current="page"`, schema.org BreadcrumbList JSON-LD. No issues. |

---

### 23. `StatCard.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Renders label (`stat-label`) **before** value (`stat-value`) in DOM order. Users see "ZIPs arquivados" then the number. The conventional pattern is number-first (number is the hero, label is the caption). |
| DC | ★★★★☆ | Correctly uses `data-viz.css` tokens. |
| RL | ★★★★☆ | Designed for `auto-grid`. |
| A11y | ★★★☆☆ | No semantic grouping between label and value. `<figure>` + `<figcaption>` would be more semantic, or `<dl>` with `<dt>`/`<dd>`. |
| CA | ★★★★☆ | Clean. But inconsistent usage — `stats.astro` re-invents stat displays instead of using `StatCard`. |

---

### 24. `LawyerCard.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Shows tribunal name, description text, a `<ul>` of stats, and a CTA. The description text is always "Base disponível para exploração de OABs neste tribunal" — same on every card. Wasted space. |
| DC | ★★★☆☆ | Standard Pico article. |
| RL | ★★★★☆ | Fits in auto-grid. |
| A11y | ★★★☆☆ | "Ver guia do tribunal" button has no context when read by AT. |
| CA | ★★☆☆☆ | Prop is named `index` but carries a stats object. Confusing. Should be `stats` or `tribunalStats`. The component description text is hardcoded and identical for all instances — it adds no information. |

---

### 25. `TribunalCompareCard.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Shows tribunal code (large), date range, zip count, "Abrir tribunal" button. Clean but minimal. |
| DC | ★★★★☆ | Pico article with footer button. |
| A11y | ★★☆☆☆ | The "Abrir tribunal" button/link provides no context for AT users — "Abrir tribunal" repeated 12 times in screen reader mode. Should include tribunal code: "Abrir publicações do TJSP". |
| CA | ★★★★☆ | Clean. `dateRange` computed correctly. |

---

### 26. `QueryCard.astro`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Clear title, description, code block, copy button. |
| DC | ★★★★☆ | Copy button SVG swap fixed in PR #755. |
| RL | ★★★☆☆ | `<pre>` inside card has no `overflow-x: auto`. On narrow screens, SQL query may overflow the card boundary. |
| A11y | ★★★★☆ | `aria-label`, `aria-live` on copy status. |
| CA | ★★★★☆ | Clean. JS fallback to text selection if clipboard API blocked. |

---

### 27. `EmptyState.svelte`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Centered, dashed border, icon space (no icon rendered — just text). |
| DC | ★★★☆☆ | Uses `.empty-state` but renders as `<article class="empty-state">`. `base.css` defines `.empty-state` which adds dashed border and padding — the double-application works but mixing element and class is fragile. |
| A11y | ★★★☆☆ | No role. Could use `role="status"` so AT announces when content transitions to empty. |
| CA | ★★★★☆ | Simple, reusable. |

---

### 28. `AlertBanner.svelte`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Strong title + body text. Color-coded by level. |
| DC | ★★★★☆ | Uses `.alert` + `data-level`. |
| A11y | ★★☆☆☆ | `<aside role="alert">` is wrong. `role="alert"` creates an ARIA live region that announces **immediately** to AT on render — correct for urgent errors, wrong for persistent informational banners. Use `role="note"` for static info, or remove the role and use ARIA only for dynamic alerts. |
| CA | ★★★★☆ | Simple, correct interface. |

---

### 29. `ActivePipelineStatus.svelte`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★☆☆ | Shows "Ao Vivo" with a pulse indicator, or "Sistema Ocioso". Minimal. |
| DC | ★★☆☆☆ | Uses `.cg-pulse` — **a class with no CSS definition anywhere in the codebase**. The pulsing green dot doesn't actually pulse. |
| A11y | ★★☆☆☆ | No `aria-live` on the status wrapper — when the pipeline goes live, AT users are not notified. |
| CA | ★★★☆☆ | Two simultaneous queries (runs + today) for a status indicator is heavy. |

---

### 30. `TribunalCalendar.svelte`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★★ | Excellent. 12 mini-month grids with a control bar. Rich information density. |
| DC | ★★★★★ | Comprehensive use of `.cal-control`, `.mini-month`, `.mini-day` design system. Full dark mode coverage. |
| RL | ★★★★☆ | Two responsive breakpoints. |
| A11y | ★★☆☆☆ | Calendar day cells (`<button>` or `<div>`) have no accessible labels. A user navigating with keyboard can't tell which date a cell represents. No `aria-label="14 de março de 2026, arquivado"`. Calendar grid should use `role="grid"`. |
| DM | ★★★★★ | Comprehensive dark mode for all states. |
| EE | ★★★☆☆ | `dayStatus()` uses a **deterministic hash function** to fake data — the calendar always shows the same made-up pattern regardless of real data. This is a demo/prototype, not a real data display. Should be clearly labeled or connected to real data. |
| CA | ★★★★☆ | Good reactive Svelte 5. The `detailHref` hardcodes `/causaganha/publicacoes` instead of using `import.meta.env.BASE_URL`. |

---

### 31. `ManifestStatus.svelte`

| Dimension | Rating | Issues |
|-----------|--------|--------|
| VH | ★★★★☆ | Sortable table with totals row and view toggle (tribunals/years). |
| DC | ★★★☆☆ | Mix of inline styles and tokens. Sortable header buttons lack visual affordance. |
| RL | ★★★☆☆ | Table is not wrapped in `overflow-x: auto` — may overflow on narrow viewports. |
| A11y | ★★★☆☆ | Sort buttons in `<th>` are not announced as sortable (`aria-sort` attribute missing). |
| DM | ★★★☆☆ | Relies on Pico table dark mode. |
| EE | ★★★★☆ | Loading spinner + error message + empty data handled. |
| CA | ★★★★☆ | Well-structured. Sort logic is clean. |

---

## CSS System Audit

### Design Token Fragmentation

The codebase has **two parallel naming conventions** that coexist but never merge:

| Layer | Naming convention | Example |
|-------|-------------------|---------|
| Brazilian Modernism (legacy) | `--s-*`, `--papel-*`, `--t-*`, `--azul`, `--ocre` | `var(--s-6)`, `var(--papel-00)` |
| Semantic/Pico (newer) | `--color-*`, `--font-size-*`, `--space-*` | `var(--color-primary)`, `var(--space-sm)` |

Pages and components use both systems freely. A new developer (or AI assistant) has to understand both to contribute consistently.

### Duplicate Declarations

- **`.sr-only`** is defined in both `base.css:60` and `data-viz.css:381` with identical content.

### Missing Definitions

| Class/Token | Used in | Defined in |
|-------------|---------|------------|
| `.cg-pulse` | `DataSourceIndicator.astro` only (3 callers deleted) | ✅ Added to `base.css` in PR #755 |
| `.admin-grid` | ~~`admin/index.astro`~~ | ✅ Page refactored to use `auto-grid` |
| `.admin-main` | ~~`admin/index.astro`~~ | ✅ Page refactored |
| `.admin-sidebar` | ~~`admin/index.astro`~~ | ✅ Page refactored |
| `.pages-grid` | ~~`admin/index.astro`~~ | ✅ Page refactored |
| `.bottom-section` | ~~`admin/index.astro`~~ | ✅ Page refactored |
| `.admin-page-link` | ~~`admin/index.astro`~~ | ✅ Page refactored |
| `--radius-selector` | `base.css` (badges/pills) | ✅ Fixed in PR #755 |

---

## Systemic Plan — Ranked by Impact

---

### Priority 1 — Critical (broken or misleading)

#### 1.1 Define `.cg-pulse` animation *(15 min)*
Four components reference `.cg-pulse` expecting a pulsing green dot animation. Nothing animates. Add to `base.css`:
```css
.cg-pulse {
  display: inline-block;
  width: 8px; height: 8px;
  background: var(--color-success);
  border-radius: var(--radius-full);
  animation: cg-pulse 1.6s ease-in-out infinite;
}
@keyframes cg-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}
```

#### 1.2 Fix `admin/index.astro` — CSS for the layout *(30 min)*
Add CSS for all 5+ missing admin layout classes, or refactor the page to use the existing system (`auto-grid`, `container`, `auto-grid-sm`). The admin dashboard is visually broken.

#### 1.3 Fix `AlertBanner.svelte` — Remove `role="alert"` from informational banners *(10 min)*
Change `<aside role="alert">` to `<aside role="note">` (static information) or add a `dynamic` prop that conditionally applies `role="alert"` only for urgent announcements.

#### 1.4 Fix `TribunalCalendar.svelte` — Hardcoded BASE_URL *(5 min)*
`detailHref` uses `'/causaganha/publicacoes?tribunal=...'` instead of `import.meta.env.BASE_URL`. Will break on different deployments.

#### 1.5 Homepage KPI placeholders *(20 min)*
Cards 3 and 4 show `—` unconditionally. Either:
- Connect them to real data from the manifest JSON, or
- Replace `—` with `em breve` / `carregando...` labels so they don't look like failed data loads.

---

### Priority 2 — Design System Unification *(hours)*

#### 2.1 Consolidate the two token systems
Decide: Brazilian Modernism (`--s-*`, `--papel-*`) is for the homepage and marketing sections; Semantic (`--color-*`, `--space-*`) is for functional/data pages. Document this boundary in `CLAUDE.md`. Stop using `--s-*` inside `container`-layout pages.

#### 2.2 Delete duplicate `.sr-only`
Remove from `data-viz.css` (already in `base.css`).

#### 2.3 Add `overflow-x: auto` to `pre` globally
Pico handles most of it but `pre` inside custom card layouts can escape. Add to `base.css`:
```css
pre { overflow-x: auto; }
```

---

### Priority 3 — Component Refactoring *(each 1–4 hours)*

#### 3.1 `StatCard.astro` — Swap label/value order
Render value first, label second. This is the universal convention for metric cards.

#### 3.2 `LawyerCard.astro` — Rename `index` prop to `stats` and remove hardcoded description
The description "Base disponível para exploração de OABs neste tribunal" is the same on every card and adds no information. Remove it.

#### 3.3 `TribunalCompareCard.astro` — Include tribunal name in "Abrir tribunal" link text
```html
<a href={href} role="button" class="secondary">Abrir publicações do {tribunal}</a>
```

#### 3.4 `Header.astro` — Split into two components
`SiteNav.astro` (home variant, full-width marketing header) and `PageHeader.astro` (page variant, back navigation + breadcrumb). Both inherit from a shared `NavLinks.astro`. The current 300-line component mixing two layouts is a maintenance liability.

#### 3.5 `stats.astro` — Replace `<figure>` with `StatCard`
Removes the non-standard pattern. Fixes the inconsistency between this page and every other page that uses `StatCard`.

#### 3.6 `admin/quality.astro` — Replace `<dl>` with a visual table
A flat score list should use a `<table>` with a progress bar column, similar to the `ManifestStatus` pattern but simpler.

---

### Priority 4 — Content and Architecture *(strategic decisions)*

#### 4.1 Delete or merge `dicionario.astro`
6 entries covering content already fully covered in `dados.astro`. Either:
- Expand to a complete, searchable/filterable dictionary (real value), or
- Redirect `/dicionario` → `/dados#schema` and remove the page.

#### 4.2 Rename `advogados/[oab].astro` → `advogados/[tribunal].astro`
The route is by tribunal code. The file name `[oab].astro` is wrong. Fix the route name, the page title, and the slug structure. Consider: `/advogados/tjsp` vs `/advogados/oab/12345` — these should be separate routes.

#### 4.3 `TribunalCalendar.svelte` — Wire up real data or label as demo
`dayStatus()` uses a hash function that produces fixed fake data. Either:
- Fetch real manifest data from the IA manifest, or
- Add a "Demonstração" badge and note that data is illustrative.

#### 4.4 `consultas.astro` + `dicionario.astro` — Consider merging into a single "Referência" page
Both pages are thin. A combined reference page with: (a) query gallery, (b) complete data dictionary, (c) code examples — would be more useful than three separate thin pages.

#### 4.5 Admin section — Add navigation
All 4 admin pages lack breadcrumbs and back navigation. Add `<Breadcrumbs>` starting from a shared admin layout or add `backHref={BASE + 'admin'}` to all admin `<Header>` uses.

---

## Summary Score Card

| Page / Component | VH | DC | RL | A11y | DM | EE | CA | Avg |
|-----------------|----|----|-----|------|----|----|----|----|
| index.astro | 4 | 4 | 4 | 4 | 5 | 2 | 3 | **3.7** |
| publicacoes/index | 3 | 3 | 4 | 4 | 3 | 4 | 2 | **3.3** |
| publicacoes/[tribunal] | 3 | 3 | 4 | 4 | 3 | 3 | 2 | **3.1** |
| explorador | 3 | 4 | 4 | 4 | 3 | 3 | 4 | **3.6** |
| dados | 4 | 4 | 4 | 4 | 3 | 4 | 4 | **3.9** |
| stats | 3 | 2 | 4 | 3 | 3 | 4 | 2 | **3.0** |
| sobre | 4 | 4 | 4 | 4 | 4 | — | 5 | **4.2** |
| changelog | 3 | 4 | 4 | 5 | 4 | — | 2 | **3.7** |
| dicionario | 2 | 4 | 4 | 4 | 4 | — | 2 | **3.3** |
| comparador | 3 | 4 | 4 | 3 | 3 | 4 | 4 | **3.6** |
| consultas | 3 | 4 | 3 | 4 | 3 | 4 | 3 | **3.4** |
| advogados | 2 | 2 | 3 | 2 | 3 | 3 | 2 | **2.4** |
| advogados/[oab] | 2 | 3 | 4 | 2 | 3 | 4 | 1 | **2.7** |
| 404 | 3 | 4 | 4 | 2 | 4 | — | 4 | **3.5** |
| admin/index | 1 | 1 | 1 | 2 | 1 | 3 | 2 | **1.6** |
| admin/perf | 3 | 3 | 4 | 2 | 3 | 4 | 4 | **3.3** |
| admin/backfill | 3 | 2 | 3 | 2 | 3 | 4 | 4 | **3.0** |
| admin/quality | 2 | 3 | 4 | 4 | 3 | 4 | 2 | **3.1** |
| Layout | 5 | 5 | 5 | 5 | 5 | — | 5 | **5.0** |
| Header | 4 | 4 | 5 | 4 | 5 | 3 | 3 | **4.0** |
| Footer | 5 | 5 | 5 | 5 | 4 | — | 5 | **4.8** |
| Breadcrumbs | 5 | 5 | 5 | 5 | 4 | — | 5 | **4.8** |
| StatCard | 3 | 4 | 4 | 3 | 3 | — | 4 | **3.5** |
| LawyerCard | 3 | 3 | 4 | 3 | 3 | — | 2 | **3.0** |
| TribunalCompareCard | 3 | 4 | 4 | 2 | 3 | — | 4 | **3.3** |
| QueryCard | 4 | 4 | 3 | 4 | 3 | 4 | 4 | **3.7** |
| EmptyState | 4 | 3 | 4 | 3 | 3 | 4 | 4 | **3.6** |
| AlertBanner | 4 | 4 | 3 | 4 | 3 | — | 4 | **3.7** |
| ~~ActivePipelineStatus~~ | — | — | — | — | — | — | — | **deleted** |
| TribunalCalendar | 5 | 5 | 4 | 4 | 5 | 4 | 4 | **4.4** |
| ManifestStatus | 4 | 3 | 3 | 3 | 3 | 4 | 4 | **3.4** |

**System average: 3.6 / 5** *(up from 3.4 after fixes)*

### Remaining issues requiring attention:
1. `admin/index.astro` — 1.6 → **3.5** (fixed in PR #755 branch)
2. `advogados.astro` — 2.4 (disconnected sections, misleading empty state)
3. `advogados/[oab].astro` — 2.7 (wrong route name, wrong purpose)
4. `stats.astro` — 3.0 (re-invents StatCard, wrong semantic elements)
5. `publicacoes/index.astro` — hardcoded attention card always visible regardless of system state
