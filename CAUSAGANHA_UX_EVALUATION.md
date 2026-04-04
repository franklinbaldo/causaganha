# CausaGanha UX & Design Evaluation

## 📊 Scores (1-10)

*   **Mobile Usability:** 4/10
    *   *Reasoning:* Core interactive elements like the Heatmap are virtually unusable on 375px screens due to tiny touch targets. Information density on mobile is high, but awkward inline flex styling causes text to squash rather than stack elegantly.
*   **Visual Polish:** 5/10
    *   *Reasoning:* While the PicoCSS foundation provides a decent baseline, the heavy use of inline styling in Preact components creates a disjointed, "prototype" feel compared to the clean Astro layouts.
*   **Data Clarity:** 7/10
    *   *Reasoning:* The data itself is present and valuable (Pipeline Status, Coverage %, Volume), but the typographic hierarchy is flat. Key metrics blend in with metadata due to arbitrary inline font sizing.
*   **Consistency (Astro vs. Preact):** 4/10
    *   *Reasoning:* There is severe friction between technologies. Astro parts leverage standard semantic tags and external CSS, whereas Preact components are littered with hardcoded, repetitive inline layout styles.

---

## 🛑 The "Sins": Top 5 Issues

1.  **Inline Style Soup (The "Anti-Pattern"):**
    Instead of relying on PicoCSS semantics or shared utility classes in `index.css`, Preact components are injected with massive, hardcoded `style={{ ... }}` objects for standard layout needs (flexbox, borders, paddings). This kills maintainability and breaks visual cohesion.
    *   *Code Reference:* `dashboard/src/components/PublicationCard.tsx:11` - `<header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--color-border-muted)'... }}>`

2.  **Microscopic Touch Targets (Mobile Accessibility):**
    The Heatmap attempts to render 365 days of cells into a single flexible container. On a 375px screen, these cells shrink far below the mandatory 24px minimum touch target size, making the tooltip interactions impossible for mobile users.
    *   *Code Reference:* `dashboard/src/components/Heatmap.tsx:143` (Cell rendering logic creates tiny targets without horizontal scrolling containers).

3.  **Muddy Typography & Hierarchy:**
    In the Publication Cards, the distinction between "Title", "Context" (e.g., Orgao), and "Action" is visually flattened. Everything is styled via subtle inline variable tweaks rather than using semantic HTML (`<h1>`, `<small>`, `<kbd>`).
    *   *Code Reference:* `dashboard/src/components/PublicationCard.tsx:18` - `<small style={{ color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)', display: 'block'... }}>`

4.  **Weak System Status / Empty States:**
    When a Tribunal has no data, the fallback is a simple string of text ("Sem dados") appended inline. It lacks a clear, visual empty state (e.g., a muted container with an icon), leaving the user guessing if the UI is broken or simply empty.
    *   *Code Reference:* `dashboard/src/components/TribunalView.tsx:109` - `{hasData ? ... : 'Sem dados'}` renders as plain text without a dedicated UI state.

5.  **Awkward Mobile Grids & Table Wrapping:**
    Data grids and tables lack robust mobile handling. Using raw CSS grids like `gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))'` can cause overflow or strange layouts on 375px screens. They need proper `.table-responsive` horizontal scrolling or explicit card-stacking behavior.
    *   *Code Reference:* `dashboard/src/components/TribunalView.tsx:96` - The 200px minimum column size breaks down on smaller screens if container paddings are applied.

---

## 🔭 Vision: 3 Actionable Changes to Look "Expensive"

1.  **Purge Inline Styles & Adopt Utility Classes:**
    Migrate all repetitive inline layout properties (flex wrappers, gaps, borders, margins) from Preact (`.tsx`) files into `dashboard/src/index.css` as semantic utility classes (e.g., `.flex-between`, `.border-bottom`). This immediately aligns the Preact components with the clean, Astro/PicoCSS aesthetic and makes the codebase feel professional.

2.  **Implement Mobile-First Horizontal Scrolling for Data Density:**
    For the Heatmap and complex data tables, abandon the attempt to squish everything onto a single vertical viewport. Wrap these components in a `.table-responsive` (or similar scrollable container) and enforce a strict `min-width` and minimum `24px` touch target size for interactive cells. This transforms a broken mobile view into a deliberate, interactive mobile-first data exploration tool.

3.  **Elevate System Feedback with Semantic States:**
    Upgrade all "loading" and "empty" states. Replace raw "Loading..." text with proper `<article aria-busy="true">` elements (leveraging PicoCSS). For empty data sets, create a dedicated `EmptyState` component featuring a muted SVG icon and clear, actionable copy, removing the ambiguity of "prototype-level" missing data.