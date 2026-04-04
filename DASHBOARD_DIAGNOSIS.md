# Polish CausaGanha Dashboard Diagnosis

## Context
A comprehensive review of the CausaGanha Astro dashboard reveals several areas that need polish across the site. The current structure is functional but lacks consistent styling, proper Portuguese diacritics in some components, and cohesive presentation, particularly in dynamic React/Preact components (`TribunalDetail`, `DateDetail`, etc.).

This diagnosis groups fixes by area (e.g., Homepage, Publication pages, Shared Components) to allow focused, incremental PRs.

---

## 1. Homepage (`index.astro`)

### Batch 1: Text / Localization
- No major localization issues found; Portuguese looks correct ("Transparência no Mercado Jurídico Brasileiro", "Dados Abertos", etc.).

### Batch 2: Layout / Styling Polish
- The Hero section's `live-card` uses inline styles extensively (e.g., `padding-bottom: var(--space-sm); border-bottom: 1px solid var(--color-border-muted);`). Move these to `<style>` classes.
- The `infra-grid` uses a hardcoded `1fr 1fr` that switches to `1fr` on mobile. Ensure spacing and margins are consistent.
- `stats-grid` has slightly unaligned typography compared to `<article>` styles (e.g., hardcoded `.stat-value` sizes). Should standardize using the `pico.css` semantics where possible.

---

## 2. Statistics Page (`stats.astro`)

### Batch 1: Text / Localization
- The word "Confiáveis" and "Falhas" are correctly localized.
- "Padrão Semanal" section: the `displayWeekly` logic truncates the day name to 3 characters using `slice(0, 3)`. Ensure days are capitalized consistently in Portuguese (e.g., `Seg`, `Ter`, `Qua`).

### Batch 2: Layout / Styling Polish
- The `weekly-grid` uses `grid-template-columns: repeat(7, 1fr)`. On small screens (mobile), it breaks into `repeat(4, 1fr)`, which leaves 3 days wrapping awkwardly. Better to use a flex container or a horizontal scrolling container on small screens.
- Inline styles used heavily in `table` and `<article>` headers (e.g., `style="border-bottom: 1px solid var(--color-border-muted);"`). Move to `<style>`.

---

## 3. Publications Index (`publicacoes/index.astro` & `TribunalView.tsx`)

### Batch 1: Text / Localization
- Text looks mostly correct.
- `TribunalView.tsx` uses "Filtre tribunais por sigla ou nome".

### Batch 2: Layout / Styling Polish
- `TribunalView.tsx` renders `<article>` blocks for "Progresso do Arquivo" with heavy inline styles (`style={{ marginBottom: 'var(--space-xl)' }}`). This needs CSS classes.
- The search bar from `IASearchBar.tsx` (rendered above `TribunalView`) looks unstyled in terms of layout container logic.
- "ZIPs por Ano" and "Progresso por Ano" grids use inline styles. Move to a CSS module or global `.css` file.

---

## 4. Tribunal Detail Page (`publicacoes/[tribunal].astro` & `TribunalDetail.tsx` & `DateDetail.tsx`)

### Batch 1: Text / Localization
- **`TribunalDetail.tsx`**: "Concluido" is missing accent -> "Concluído".
- **`TribunalDetail.tsx`**: "Completed" and "In progress" -> "Concluído" and "Em andamento".
- **`DateDetail.tsx`**: English/Portuguese mix: "1min atras" -> "1 min atrás", "1h atras" -> "1h atrás", "1d atras" -> "1d atrás".
- **`DateDetail.tsx`**: "Carregando publicacoes..." -> "Carregando publicações...".
- **`DateDetail.tsx`**: "Ver todas as publicacoes" -> "Ver todas as publicações".
- **`DateDetail.tsx`**: "Nenhuma publicacao encontrada." -> "Nenhuma publicação encontrada."
- **`DateDetail.tsx`**: "Pagina {x} de {y}" -> "Página {x} de {y}".
- **`DateDetail.tsx`**: "{x} pag." -> "{x} pág."
- **`DateDetail.tsx`**: "{x} publicacoes" -> "{x} publicações".
- **`Heatmap.tsx`**: "Velocity Timeline" -> "Velocidade de Coleta" (or similar Portuguese equivalent). "docs/sem (média)" -> "dias/sem (média)".

### Batch 2: Layout / Styling Polish
- **`DateDetail.tsx`**: The list of publications renders inside raw `<div>` tags without semantic structure or proper Pico.css layout classes. For example, the header showing `{dateStr}` is just a `<div>` containing an `<h3>` and a few `<span>`s. It should be wrapped in an `<article>` or a proper `<header>`.
- **`DateDetail.tsx`**: The link/share section `<div>` uses generic `<a href>` elements. Needs Pico CSS styling like `role="button" class="secondary outline"`.
- **`Heatmap.tsx`**: Extensive inline styles (e.g., `style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}`). These are React components so inline styles are somewhat acceptable, but abstracting repetitive flexbox patterns to shared classes (`.flex-col`, `.gap-sm`) would clean up the JSX.

---

## 5. Shared Components (`Header.astro`, `PublicationCard.tsx`, etc.)

### Batch 1: Text / Localization
- **`PublicationCard.tsx`**: "Próxima" should ideally be paired with "Anterior" (both correct).
- **`LiveStatusWidget.tsx`**: "Live pipeline status currently unavailable." -> "Status ao vivo indisponível."
- **`LiveStatusWidget.tsx`**: "Loading pipeline status..." -> "Carregando status do pipeline..."
- **`LiveStatusWidget.tsx`**: "Pipeline Running" -> "Pipeline em Execução"
- **`LiveStatusWidget.tsx`**: "Updated" -> "Atualizado às"
- **`LiveStatusWidget.tsx`**: "ZIPs Uploaded" -> "ZIPs Enviados"
- **`LiveStatusWidget.tsx`**: "Active Tribunals" -> "Tribunais Ativos"
- **`NetworkStatusBanner.tsx`**: Entirely in English ("Slow Network Detected", "Retrying..."). Translate to Portuguese ("Rede Lenta Detectada", "Tentando novamente...").

### Batch 2: Layout / Styling Polish
- **`PublicationCard.tsx`**: Lots of inline styles for margins and typography (e.g., `fontFamily: "'JetBrains Mono', monospace"`).
- **`Breadcrumbs.astro`**: Needs to ensure link contrast against `--color-content-tertiary`.

---

## 6. Admin / Internal Tools (`PRGateExplainer.tsx`)
- Fully English, which is fine for an admin tool, but could be localized. Lower priority.

## Next Steps
This plan suggests creating a single cohesive PR addressing **Batch 1 (Portuguese Text Corrections)** and **Batch 2 (Layout / Styling Polish)** specifically for the Tribunal Detail / Publication surfaces (`TribunalDetail.tsx`, `DateDetail.tsx`, `PublicationCard.tsx`, `Heatmap.tsx`), as these are the most interactive and data-heavy parts of the dashboard and exhibit the most mixed-language/unstyled rough edges.
