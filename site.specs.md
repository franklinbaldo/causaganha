# CausaGanha Dashboard — Client Specifications

**Version:** 1.0
**Date:** January 2026
**Status:** Ready for Development

---

## 1. Overview

### 1.1 Project Purpose

CausaGanha is building a comprehensive archive of Brazilian judicial communications to enable transparent lawyer performance analytics. This dashboard monitors the data collection pipeline in real-time.

### 1.2 Problem Statement

The data pipeline runs automatically every 5 minutes, collecting judicial publications from 91 Brazilian courts. Stakeholders need visibility into:

- Whether collection is succeeding or failing
- Which courts have data and which don't
- Historical collection patterns over time
- Volume of data being archived

### 1.3 Solution

A real-time monitoring dashboard that pulls data from Internet Archive (storage) and GitHub Actions (pipeline execution) to provide operational visibility.

---

## 2. Target Users

| User Type | Needs | Frequency |
|-----------|-------|-----------|
| Project Owner | Overall health check, identify problems | Daily |
| Developers | Debug failures, check specific tribunal status | When issues arise |
| Curious Visitors | Understand what the project does | One-time |

---

## 3. Data Sources

### 3.1 Internet Archive Metadata API

**Endpoint:** `https://archive.org/metadata/djen-{YYYY-MM-DD}`

**Purpose:** Retrieve information about archived files for each day.

**Response Structure (relevant fields):**

```json
{
  "item_size": 710850085,
  "files": [
    {
      "name": "djen-2026-01-28-TJSP.zip",
      "size": "121396165",
      "format": "ZIP",
      "filecount": "225"
    },
    {
      "name": "djen-2026-01-28-STF.absent",
      "size": "32",
      "format": "Unknown"
    }
  ],
  "metadata": {
    "identifier": "djen-2026-01-28",
    "date": "2026-01-28",
    "title": "DJEN Data - 2026-01-28"
  }
}
```

**File Naming Convention:**

- `djen-{date}-{TRIBUNAL}.zip` → Data successfully collected
- `djen-{date}-{TRIBUNAL}.absent` → No publication that day (expected)
- Missing file → Collection pending or failed

**Rate Limits:** None documented, but recommend caching and reasonable polling intervals.

### 3.2 GitHub Actions API

**Endpoint:** `https://api.github.com/repos/franklinbaldo/causaganha/actions/runs`

**Purpose:** Retrieve pipeline execution history.

**Response Structure (relevant fields):**

```json
{
  "workflow_runs": [
    {
      "id": 21463186936,
      "name": "Data Pipeline",
      "run_number": 1110,
      "status": "completed",
      "conclusion": "success",
      "created_at": "2026-01-29T02:22:53Z",
      "html_url": "https://github.com/.../runs/21463186936"
    }
  ]
}
```

**Conclusion Values:** `success`, `failure`, `cancelled`, `skipped`
**Status Values:** `queued`, `in_progress`, `completed`

**Rate Limits:** 60 requests/hour unauthenticated, 5000/hour with token.

---

## 4. Features & Components

### 4.1 Header

| Element | Description |
|---------|-------------|
| Logo | "causaganha" — "causa" in accent color, "ganha" in white |
| Subtitle | "Monitor do Pipeline DJEN" |
| System Status | Indicator showing Operational/Degraded/Failure |
| Clock | Real-time clock (user's timezone) |

**System Status Logic:**

- 🟢 **Operacional** — ≥80% of last 10 runs successful
- 🟡 **Degradado** — 50-79% successful
- 🔴 **Falha** — <50% successful

### 4.2 Metrics Cards

Four cards in a row (2x2 on mobile):

| Metric | Source | Calculation |
|--------|--------|-------------|
| **Arquivos Hoje** | IA API | Count of `.zip` files in today's item |
| **Volume Hoje** | IA API | `item_size` from today's metadata |
| **Dias Arquivados** | IA API | Count of days with existing items (sample) |
| **Saúde do Pipeline** | GitHub API | % of successful runs in last 10 |

**Display:** Large number, small label below, muted description.

### 4.3 Activity Calendar (GitHub-style)

**Purpose:** Visualize collection history over ~16 weeks.

**Layout:**

```
         Jan        Feb        Mar
Mon  ░░░░░░░░░░░░░░░░░░░░░░░░
     ░░░░░░░░░░░░░░░░░░░░░░░░
Wed  ░▓▓▓▓▓░▓▓▓▓▓░▓▓▓▓▓░▓▓▓▓
     ░░░░░░░░░░░░░░░░░░░░░░░░
Fri  ░▓▓▓▓▓░▓▓▓▓▓░▓▓▓▓▓░▓▓▓▓
     ░░░░░░░░░░░░░░░░░░░░░░░░
Sun  ░░░░░░░░░░░░░░░░░░░░░░░░
```

**Grid Structure:**

- Columns = weeks (16 weeks ≈ 4 months)
- Rows = days of week (Monday at top, Sunday at bottom)
- Each cell = 12x12px with 4px gap

**Color Scale (by data volume):**

| Level | Condition | Color |
|-------|-----------|-------|
| 0 | No data / pending | `#1e2d27` (border gray) |
| 1 | 1-25% of max | `rgba(34,197,94,0.2)` |
| 2 | 26-50% of max | `rgba(34,197,94,0.4)` |
| 3 | 51-75% of max | `rgba(34,197,94,0.7)` |
| 4 | 76-100% of max | `#22c55e` (full green) |

**Legend:** "Menos" → color scale boxes → "Mais"

**Interactions:**

- Hover: Scale up 1.5x, show tooltip with date + size + tribunal count
- Click: Open `https://archive.org/details/djen-{date}` in new tab

**Stats Row Below Calendar:**

- Total coletado: Sum of all item_size
- Dias com dados: Count of days with data
- Maior dia: Date with largest item_size

### 4.4 Tribunal Heatmap

**Purpose:** Show status of each of the 91 courts for the most recent day with data.

**Organization (4 groups):**

| Group | Courts |
|-------|--------|
| Superiores | STF, STJ, TST, TSE, STM, CNJ |
| TRFs | TRF1, TRF2, TRF3, TRF4, TRF5, TRF6 |
| TRTs | TRT1 through TRT24 |
| TJs | TJAC, TJAL, TJAM, TJAP, TJBA, TJCE, TJDFT, TJES, TJGO, TJMA, TJMG, TJMS, TJMT, TJPA, TJPB, TJPE, TJPI, TJPR, TJRJ, TJRN, TJRO, TJRR, TJRS, TJSC, TJSE, TJSP, TJTO |

**Cell Display:**

- Compact pill/badge showing tribunal code (e.g., "TJSP")
- Background color indicates status

**Status Colors:**

| Status | Meaning | Color |
|--------|---------|-------|
| OK | `.zip` file exists | Green `#22c55e` |
| Absent | `.absent` file exists | Yellow `#eab308` |
| Error | File expected but missing | Red `#ef4444` |
| Pending | Not yet processed | Gray `#6b7280` at 30% opacity |

**Interactions:**

- Hover: Scale up 1.1x, show tooltip with tribunal name + file size or status
- Click (optional): Open filtered view for that tribunal

**Header:** "Status por Tribunal" + "(YYYY-MM-DD)" showing which day is displayed

### 4.5 Recent Executions List

**Purpose:** Show GitHub Actions run history.

**Display:** 8 most recent runs in a vertical list.

**Each Item Shows:**

- Status icon (✓ success, ✗ failure, ⊘ cancelled/skipped, ◌ in progress)
- Workflow name
- Run number (#1234)
- Time ago (e.g., "5min", "2h", "1d")

**Interactions:**

- Click: Open `html_url` in new tab

**Header:** "Execuções Recentes" with "Ver todas →" link to GitHub Actions page

### 4.6 Recent Days List

**Purpose:** Quick access to last 5 days of archived data.

**Each Item Shows:**

- Status indicator (green dot if data exists)
- Date (YYYY-MM-DD format)
- Tribunal count (number of `.zip` files)
- Total size

**Interactions:**

- Click: Open `https://archive.org/details/djen-{date}` in new tab

**Header:** "Últimos Dias" with "Internet Archive →" link

### 4.7 Info Section

**Purpose:** Explain the project to first-time visitors.

**Content:**
> **O que é isso?** Este dashboard monitora a coleta diária de comunicações judiciais do DJEN (Diário de Justiça Eletrônico Nacional). Os dados são arquivados permanentemente no Internet Archive para possibilitar análises de performance jurídica.

**Links:** GitHub, Internet Archive

---

## 5. Design Requirements

> **🎯 Design Goal:** This dashboard should be so beautiful that users keep it open on a second monitor just to look at it. It's a showcase of what CausaGanha stands for — transparency, precision, and craft.

### 5.0 Design Principles

1. **Data is the hero** — The numbers and visualizations should be the stars. UI chrome fades into the background.

2. **Calm confidence** — The interface should feel stable and trustworthy, like a well-engineered control room. No flashiness, no gimmicks.

3. **Reward attention to detail** — Users who look closely should discover subtle touches that delight them.

4. **Dark done right** — Not just "slap dark colors on it." True dark theme mastery with proper contrast, depth, and eye comfort.

5. **Motion with purpose** — Every animation should communicate something. Loading, success, attention, hierarchy.

### 5.1 Visual Style

| Aspect | Specification |
|--------|---------------|
| Overall Feel | Dark terminal/hacker aesthetic, but clean and professional |
| Mood | Technical, trustworthy, data-focused |
| Inspiration | GitHub contribution graph, Vercel dashboard, Linear app, Raycast |

### 5.2 Beauty & Polish Requirements

**This dashboard should feel premium and delightful to use.** It's not just functional — it should make users want to keep it open. Think: "I could stare at this all day."

#### Visual Hierarchy & Spacing

- **Generous whitespace** — Don't cram elements. Let the data breathe.
- **Consistent spacing scale** — Use 4px base unit (4, 8, 12, 16, 24, 32, 48)
- **Clear visual hierarchy** — Most important info (system status, today's metrics) should pop
- **Alignment** — Everything on a grid. No orphaned elements.

#### Depth & Dimension

- **Subtle shadows** — Cards should feel slightly elevated, not flat
- **Border glow on focus/hover** — Soft green glow (`0 0 20px rgba(34,197,94,0.15)`)
- **Layered backgrounds** — Header slightly different from body, cards distinct from background
- **Glass morphism (subtle)** — Header with `backdrop-blur` for depth when scrolling

#### Motion & Animation

| Element | Animation | Timing |
|---------|-----------|--------|
| Page load | Fade in + slight upward movement | 300ms ease-out |
| Cards appearing | Stagger animation (each card 50ms delay) | 400ms ease-out |
| Numbers counting | Animate from 0 to final value | 600ms ease-out |
| Status pulse | Gentle breathing glow | 2s infinite |
| Hover states | Smooth color/scale transitions | 150-200ms ease |
| Calendar cells | Scale + subtle glow on hover | 100ms ease |
| Data refresh | Subtle flash/shimmer when updated | 300ms |
| Loading skeletons | Smooth gradient shimmer | 1.5s infinite |

**Animation Principles:**

- Never jarring — all motion should feel natural
- Purposeful — animation draws attention to important changes
- Performant — use `transform` and `opacity` only, never animate layout properties
- Respect `prefers-reduced-motion` media query

#### Micro-interactions

- **Hover feedback on everything clickable** — User should never wonder "can I click this?"
- **Active/pressed states** — Slight scale down (0.98) on click
- **Success feedback** — Brief green flash when data refreshes successfully
- **Tooltips** — Appear with fade + slight Y translation (not instant pop)
- **Focus rings** — Visible, attractive focus states for keyboard navigation

#### Data Visualization Excellence

- **Calendar heatmap:**
  - Cells should have subtle rounded corners (2px)
  - Color transitions between levels should feel smooth
  - Consider subtle inner shadow on cells for depth
  - Weekend columns could be slightly dimmer

- **Tribunal heatmap:**
  - Pills should have consistent padding
  - Text should be perfectly centered
  - Consider subtle gradient on colored backgrounds
  - Group headers should have understated styling

- **Metric cards:**
  - Numbers should be the hero — large, bold, impossible to miss
  - Consider subtle background pattern or gradient
  - Icons (optional) should be minimal, line-style

#### Typography Polish

- **Number formatting** — Use tabular figures (monospace numbers) for alignment
- **Letter spacing** — Slightly increased on uppercase labels (0.05em)
- **Line height** — Generous for readability (1.5 for body, 1.2 for headings)
- **Font smoothing** — Enable antialiasing (`-webkit-font-smoothing: antialiased`)

#### Color Refinement

- **Gradients** — Subtle gradients on accent elements (not flat colors)
- **Green variations:**

  ```
  Success gradient: linear-gradient(135deg, #22c55e, #16a34a)
  Glow: rgba(34,197,94,0.2)
  Muted: rgba(34,197,94,0.1)
  ```

- **Dark theme depth** — Multiple shades of dark, not just one black
- **Color meaning** — Consistent across all elements (green=good, yellow=warning, red=bad)

#### Finishing Touches

- **Favicon** — Custom icon matching the brand
- **Page title** — Dynamic: "✓ CausaGanha" when healthy, "⚠ CausaGanha" when degraded
- **Cursor styles** — `pointer` on interactive elements, `default` elsewhere
- **Selection color** — Custom highlight color matching theme
- **Scrollbar styling** — Thin, subtle, matches dark theme (WebKit)
- **No layout shift** — Reserve space for loading content to prevent jumps

### 5.3 Design Inspiration & References

Study these for visual inspiration:

| Reference | What to Learn |
|-----------|---------------|
| [Linear.app](https://linear.app) | Elegant dark UI, smooth animations, attention to detail |
| [Vercel Dashboard](https://vercel.com/dashboard) | Clean data presentation, real-time updates |
| [GitHub Contribution Graph](https://github.com) | Heatmap visualization, tooltips |
| [Raycast](https://raycast.com) | Premium dark aesthetic, micro-interactions |
| [Supabase Dashboard](https://supabase.com) | Developer-focused, beautiful dark theme |
| [Stripe Dashboard](https://stripe.com) | Data density without clutter |
| [Craft.do](https://craft.do) | Typography excellence, spacing |

### 5.4 Quality Checklist

Before considering the design complete:

- [ ] Every interactive element has hover, focus, and active states
- [ ] Animations are smooth at 60fps
- [ ] No layout shifts during loading
- [ ] Works beautifully at every viewport width (not just breakpoints)
- [ ] Colors have sufficient contrast (WCAG AA minimum)
- [ ] Loading states are polished, not placeholder
- [ ] Empty states are designed, not afterthoughts
- [ ] Looks good in screenshots (people will share this)
- [ ] Feels fast even when data is loading
- [ ] Dark theme is easy on the eyes for extended viewing

### 5.5 "Wow Factor" Details

These small touches separate good from great:

| Detail | Implementation |
|--------|----------------|
| **Animated gradient background** | Subtle, slow-moving gradient on the page background (barely perceptible) |
| **Glow effects** | Active/important elements have soft colored glow |
| **Number transitions** | When data updates, numbers animate to new values (count up/down) |
| **Stagger animations** | Cards and list items appear one after another, not all at once |
| **Status pulse** | Breathing glow animation on the system status indicator |
| **Cursor trails** | Optional: subtle trail following cursor on desktop |
| **Sound design** | Optional: subtle sounds for key events (refresh complete, error) |
| **Real-time feel** | Clock with smooth animation, data that feels alive |
| **Connection status** | Visual indicator when reconnecting/offline |
| **Celebratory moments** | When health hits 100%, show confetti or special animation |

### 5.6 Dark Theme Mastery

Getting dark themes right is hard. Follow these rules:

**DO:**

- Use multiple shades of dark (not just #000)
- Increase contrast for important elements
- Use colored accents sparingly — they pop more in dark mode
- Test in actual dark room conditions
- Use slightly warm/tinted grays, not pure gray

**DON'T:**

- Use pure white (#fff) text — use #e5e7eb or similar
- Make everything the same shade of dark
- Overuse neon/bright colors (causes eye strain)
- Forget about focus states (they're more important in dark mode)
- Use dark shadows (use light/glow instead)

**Elevation levels (each level slightly lighter):**

```
Level 0 (page bg):     #0a0f0d
Level 1 (cards):       #111916
Level 2 (elevated):    #1a2420
Level 3 (hover):       #243029
Level 4 (active):      #2d3d34
```

### 5.7 Mobile Excellence

Mobile isn't an afterthought — many users will check status on their phones:

- **Touch targets** — Minimum 44x44px for all interactive elements
- **Thumb-friendly** — Important actions reachable with one hand
- **Swipe gestures** — Consider swipe to refresh
- **Reduced motion** — Simpler animations on mobile for performance
- **Offline indicator** — Clear status when connection lost
- **Pull to refresh** — Native-feeling refresh gesture
- **Responsive calendar** — Horizontal scroll on mobile, show fewer weeks

### 5.8 Screenshot-Ready Design

People will screenshot this dashboard to share status. Optimize for it:

- **Clear at any crop** — Each section should make sense in isolation
- **Brand visible** — Logo always visible in reasonable screenshots
- **Status prominent** — Key metrics readable even in thumbnails
- **No awkward cutoffs** — Design for common screenshot boundaries
- **Social preview** — Add OpenGraph meta tags for link previews

### 5.2 Color Palette

```
Background:      #0a0f0d (near black with green tint)
Card Background: #111916 (dark green-gray)
Border:          #1e2d27 (subtle green-gray)
Text Primary:    #e5e7eb (light gray)
Text Muted:      #6b7280 (medium gray)
Accent Green:    #22c55e (success, primary accent)
Accent Yellow:   #eab308 (warning, absent)
Accent Red:      #ef4444 (error, failure)
Accent Blue:     #3b82f6 (links)
```

### 5.3 Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Logo/Code | JetBrains Mono | 700 | 20px |
| Numbers/Data | JetBrains Mono | 500 | varies |
| Body | Inter | 400 | 14px |
| Labels | Inter | 500 | 12px (uppercase, tracking) |
| Small/Muted | Inter | 400 | 12px |

### 5.4 Responsive Breakpoints

| Breakpoint | Layout Changes |
|------------|----------------|
| < 640px (mobile) | Metrics 2x2, single column sections, calendar horizontal scroll |
| 640-1024px (tablet) | Metrics 2x2, two-column layout for lists |
| > 1024px (desktop) | Metrics 4x1, two-column layout, full calendar |

### 5.5 Loading States

- Use skeleton loaders (animated gradient shimmer) for all data-dependent elements
- Minimum display time: 300ms (avoid flash)
- Progressive loading: Show structure immediately, populate data as it arrives

### 5.6 Empty/Error States

| Condition | Display |
|-----------|---------|
| API timeout | "Não foi possível carregar" with retry option |
| No data for today | Show most recent day with data instead |
| Future dates in calendar | Empty cell (no color, no interaction) |

---

## 6. Technical Requirements

### 6.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Framework** | **Astro** | Islands architecture — static-first with selective hydration |
| **Styling** | Tailwind CSS | Built-in Astro support, matches design system |
| **Hosting** | GitHub Pages | Free, automatic deploy via Astro's static adapter |
| **Islands** | Svelte or React | For interactive components (team preference) |

### 6.2 Why Astro

Astro's "islands architecture" is ideal for this dashboard:

- **Static-first** — Most of the UI is presentational HTML/CSS that ships instantly
- **Selective hydration** — Only interactive parts load JavaScript
- **Fast by default** — Easy to hit Lighthouse > 90 without optimization work
- **Tailwind built-in** — Zero config needed
- **Framework-agnostic islands** — Use React, Svelte, Vue, or vanilla JS where needed
- **Simple deploy** — `@astrojs/static` adapter → push to GitHub Pages

### 6.3 Architecture: Static vs Islands

**Static Components (no JS shipped):**

| Component | Notes |
|-----------|-------|
| Header layout | Logo, subtitle, structure |
| Metric cards structure | Labels, descriptions, layout |
| Calendar grid structure | Month labels, day labels, cell grid |
| Tribunal heatmap structure | Group headers, grid layout |
| Lists structure | Section headers, item layouts |
| Info section | 100% static content |
| Footer | Links, text |

**Island Components (hydrated with JS):**

| Island | Responsibility | Hydration |
|--------|----------------|-----------|
| `<Clock />` | Real-time clock display | `client:load` |
| `<SystemStatus />` | Fetch health, show status badge | `client:load` |
| `<MetricValue />` | Fetch & animate numbers | `client:load` |
| `<ActivityCalendar />` | Fetch data, render cells, tooltips, clicks | `client:visible` |
| `<TribunalHeatmap />` | Fetch data, render status, tooltips | `client:visible` |
| `<ActionsList />` | Fetch GitHub API, render items | `client:visible` |
| `<RecentDays />` | Fetch IA API, render items | `client:visible` |
| `<Tooltip />` | Shared tooltip component | `client:load` |

### 6.4 Astro Project Structure

```
causaganha-dashboard/
├── astro.config.mjs
├── tailwind.config.mjs
├── package.json
├── public/
│   ├── favicon.svg
│   └── og-image.png
├── src/
│   ├── layouts/
│   │   └── Layout.astro          # Base HTML, meta tags, fonts
│   ├── components/
│   │   ├── Header.astro          # Static header structure
│   │   ├── MetricCard.astro      # Static card wrapper
│   │   ├── Section.astro         # Reusable section wrapper
│   │   └── InfoSection.astro     # Static info content
│   ├── islands/                   # Interactive components
│   │   ├── Clock.tsx             # Real-time clock
│   │   ├── SystemStatus.tsx      # Health indicator
│   │   ├── MetricValue.tsx       # Animated number
│   │   ├── ActivityCalendar.tsx  # GitHub-style heatmap
│   │   ├── TribunalHeatmap.tsx   # Court status grid
│   │   ├── ActionsList.tsx       # GitHub runs list
│   │   ├── RecentDays.tsx        # IA items list
│   │   └── Tooltip.tsx           # Shared tooltip
│   ├── lib/
│   │   ├── api.ts                # API fetch functions
│   │   ├── constants.ts          # Tribunal lists, colors
│   │   ├── format.ts             # formatBytes, formatTimeAgo
│   │   └── types.ts              # TypeScript interfaces
│   ├── styles/
│   │   └── global.css            # Tailwind + custom CSS
│   └── pages/
│       └── index.astro           # Main dashboard page
└── README.md
```

### 6.5 Hydration Strategies

Astro provides different hydration directives — use them strategically:

| Directive | When to Use | Components |
|-----------|-------------|------------|
| `client:load` | Immediately needed | Clock, SystemStatus, above-fold metrics |
| `client:visible` | When scrolled into view | Calendar, Heatmap, Lists |
| `client:idle` | After page is idle | Non-critical enhancements |
| `client:media` | Based on media query | Mobile-specific interactions |

**Example usage in index.astro:**

```astro
---
import Layout from '../layouts/Layout.astro';
import Header from '../components/Header.astro';
import MetricCard from '../components/MetricCard.astro';
import Clock from '../islands/Clock';
import SystemStatus from '../islands/SystemStatus';
import MetricValue from '../islands/MetricValue';
import ActivityCalendar from '../islands/ActivityCalendar';
import TribunalHeatmap from '../islands/TribunalHeatmap';
---

<Layout title="CausaGanha | Monitor do Pipeline DJEN">
  <Header>
    <SystemStatus client:load />
    <Clock client:load />
  </Header>

  <main>
    <!-- Metrics: load immediately (above fold) -->
    <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard label="Arquivos Hoje" subtitle="tribunais com dados">
        <MetricValue client:load type="filesToday" />
      </MetricCard>
      <!-- ... more cards -->
    </section>

    <!-- Calendar: load when visible (may be below fold on mobile) -->
    <ActivityCalendar client:visible />

    <!-- Heatmap: load when visible -->
    <TribunalHeatmap client:visible />
  </main>
</Layout>
```

### 6.6 Shared State Strategy

Islands are isolated by default. For shared state (e.g., fetched data used by multiple islands):

**Option A: Nano Stores (recommended)**

```typescript
// src/lib/stores.ts
import { atom } from 'nanostores';

export const $todayData = atom(null);
export const $healthData = atom(null);

// Islands subscribe to these stores
```

**Option B: Custom Events**

```typescript
// One island fetches, dispatches event
window.dispatchEvent(new CustomEvent('data-loaded', { detail: data }));

// Other islands listen
window.addEventListener('data-loaded', (e) => { ... });
```

**Option C: Fetch in Astro, pass as props**

```astro
---
// Fetch at build time or SSR
const todayData = await fetchTodayData();
---
<MetricValue client:load data={todayData} />
```

Recommend **Option A (Nano Stores)** for this dashboard — clean, reactive, works across frameworks.

### 6.7 API Module

```typescript
// src/lib/api.ts

const IA_BASE = 'https://archive.org/metadata/djen-';
const GITHUB_API = 'https://api.github.com/repos/franklinbaldo/causaganha/actions/runs';

export async function fetchIAMetadata(date: string) {
  const res = await fetch(`${IA_BASE}${date}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchGitHubRuns(count = 10) {
  const res = await fetch(`${GITHUB_API}?per_page=${count}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.workflow_runs || [];
}

export function processIAFiles(metadata) {
  // Extract tribunal statuses from files array
  // Returns: { TJSP: { status: 'ok', size: 123456 }, ... }
}
```

### 6.8 Configuration Files

**astro.config.mjs:**

```javascript
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import react from '@astrojs/react'; // or svelte

export default defineConfig({
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [
    tailwind(),
    react(), // for islands
  ],
  output: 'static',
});
```

**tailwind.config.mjs:**

```javascript
export default {
  content: ['./src/**/*.{astro,html,js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0f0d',
          card: '#111916',
          border: '#1e2d27',
          green: '#22c55e',
          yellow: '#eab308',
          red: '#ef4444',
          blue: '#3b82f6',
          muted: '#6b7280',
          text: '#e5e7eb',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
};
```

### 6.9 GitHub Actions Deploy

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Rebuild every 6 hours (optional, for any build-time data)

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v4
        id: deployment
```

### 6.10 Performance Targets

| Metric | Target | Astro Advantage |
|--------|--------|-----------------|
| First Contentful Paint | < 1.0s | Static HTML ships instantly |
| Largest Contentful Paint | < 1.5s | No JS blocking render |
| Time to Interactive | < 2.5s | Only islands need hydration |
| Total Blocking Time | < 100ms | Minimal JS, deferred loading |
| Cumulative Layout Shift | < 0.05 | Static structure prevents shifts |
| Lighthouse Score | > 95 | Astro sites routinely hit 100 |
| JS Bundle Size | < 50KB | Only interactive code ships |

### 6.11 API Strategy

**Client-side fetching in islands:**

Since this is a static site, all API calls happen client-side in the islands:

1. **On mount:** Each island fetches its required data
2. **Shared fetches:** Use Nano Stores to avoid duplicate requests
3. **Auto-refresh:** Set up intervals in top-level islands (5 min default)
4. **Error handling:** Each island handles its own errors gracefully

**Fetch orchestration:**

```typescript
// src/lib/dataLoader.ts
import { $todayData, $recentDays, $githubRuns, $isLoading } from './stores';

export async function loadAllData() {
  $isLoading.set(true);

  const [today, ...recentResults] = await Promise.all([
    fetchIAMetadata(formatDate(new Date())),
    ...getLast5Days().map(d => fetchIAMetadata(d)),
  ]);

  const runs = await fetchGitHubRuns(10);

  $todayData.set(today);
  $recentDays.set(recentResults);
  $githubRuns.set(runs);
  $isLoading.set(false);
}

// Call on app init + every 5 minutes
```

**Calendar data (sampled):**

- Fetch every 3rd day to reduce API calls
- Load progressively in background
- Cache in localStorage

### 6.12 Caching Strategy

All caching is client-side since this is a static site:

| Data | Cache Location | TTL | Key Pattern |
|------|----------------|-----|-------------|
| IA metadata (past days) | localStorage | 24 hours | `ia-{date}` |
| IA metadata (today) | memory (store) | 5 minutes | — |
| GitHub runs | memory (store) | 2 minutes | — |
| Calendar data | localStorage | 1 hour | `calendar-{date}` |

**Cache utility:**

```typescript
// src/lib/cache.ts
export function getCached<T>(key: string, ttlMs: number): T | null {
  const item = localStorage.getItem(key);
  if (!item) return null;

  const { data, timestamp } = JSON.parse(item);
  if (Date.now() - timestamp > ttlMs) {
    localStorage.removeItem(key);
    return null;
  }
  return data;
}

export function setCache(key: string, data: unknown): void {
  localStorage.setItem(key, JSON.stringify({
    data,
    timestamp: Date.now(),
  }));
}
```

### 6.13 Error Handling

Each island handles its own errors — partial failures don't break the whole page:

```typescript
// Pattern for islands
function MyIsland() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton />;
  if (error) return <ErrorState onRetry={refetch} />;
  return <DataDisplay data={data} />;
}
```

**Error states per component:**

- Show skeleton during loading
- Show friendly error message + retry button on failure
- Log errors to console for debugging
- Never show blank/broken UI

**Global error boundary (optional):**
For catching unexpected errors in React islands.

---

## 7. Interactions Specification

### 7.1 Hover Effects

| Element | Effect | Timing |
|---------|--------|--------|
| Tribunal cells | Scale 1.1x, show tooltip | 200ms ease |
| Calendar cells | Scale 1.5x, show tooltip | 100ms ease |
| List items | Border color change | 150ms ease |
| Links | Underline | instant |

### 7.2 Click Actions

| Element | Action |
|---------|--------|
| Calendar cell | Open IA item page (new tab) |
| Recent day item | Open IA item page (new tab) |
| Execution item | Open GitHub run page (new tab) |
| Tribunal cell | (Optional) Filter/highlight related data |
| Logo | (Optional) Scroll to top |

### 7.3 Tooltips

**Style:**

- Dark background (`#0a0f0d`)
- Border (`#1e2d27`)
- Positioned above element, centered
- Max width 200px
- 8px padding, 4px border-radius

**Content Format:**

```
[Bold Title]
[Muted details line 1]
[Muted details line 2]
```

---

## 8. Content & Copy

### 8.1 Labels (Portuguese)

| Key | Text |
|-----|------|
| header.title | causaganha |
| header.subtitle | Monitor do Pipeline DJEN |
| status.operational | Operacional |
| status.degraded | Degradado |
| status.failure | Falha |
| metric.files.title | Arquivos Hoje |
| metric.files.subtitle | tribunais com dados |
| metric.size.title | Volume Hoje |
| metric.size.subtitle | dados brutos |
| metric.days.title | Dias Arquivados |
| metric.days.subtitle | no Internet Archive |
| metric.health.title | Saúde do Pipeline |
| metric.health.subtitle | últimas 10 runs |
| activity.title | Atividade de Coleta |
| activity.less | Menos |
| activity.more | Mais |
| activity.stat.total | Total coletado |
| activity.stat.days | Dias com dados |
| activity.stat.biggest | Maior dia |
| tribunals.title | Status por Tribunal |
| tribunals.group.superior | Superiores |
| tribunals.group.trf | Tribunais Regionais Federais |
| tribunals.group.trt | Tribunais Regionais do Trabalho |
| tribunals.group.tj | Tribunais de Justiça |
| tribunals.status.ok | OK |
| tribunals.status.absent | Vazio |
| tribunals.status.error | Falha |
| tribunals.status.pending | Pendente |
| runs.title | Execuções Recentes |
| runs.viewAll | Ver todas → |
| days.title | Últimos Dias |
| days.viewAll | Internet Archive → |
| info.title | O que é isso? |
| info.body | Este dashboard monitora a coleta diária de comunicações judiciais do DJEN (Diário de Justiça Eletrônico Nacional). Os dados são arquivados permanentemente no Internet Archive para possibilitar análises de performance jurídica. |
| error.loading | Não foi possível carregar |
| time.now | agora |
| time.minutes | min |
| time.hours | h |
| time.days | d |

### 8.2 Tooltips Content

**Calendar Cell:**

```
{YYYY-MM-DD}
{size} • {count} tribunais
```

**Tribunal Cell (OK):**

```
{TRIBUNAL}
{size}
```

**Tribunal Cell (Absent):**

```
{TRIBUNAL}
Sem publicação
```

---

## 9. Future Considerations

### 9.1 Phase 2 Features (Not in Scope Now)

| Feature | Description |
|---------|-------------|
| Email alerts | Notify on pipeline failure |
| Historical charts | Line graph of volume over time |
| Tribunal detail view | Click tribunal to see its history |
| Search | Find specific date or tribunal |
| Embed widget | Small status badge for external sites |
| i18n | English translation |

### 9.2 Data Schema Evolution

The underlying data schema may evolve. Dashboard should be resilient to:

- New tribunals being added
- File naming convention changes
- Additional metadata fields

### 9.3 Authentication

Currently no authentication needed. Future consideration for:

- Rate limit bypass with GitHub token
- Admin features (manual refresh, cache clear)

---

## 10. Acceptance Criteria

### 10.1 Must Have (MVP)

- [ ] Header with logo, status indicator, and clock
- [ ] Four metric cards with real data
- [ ] Activity calendar with 16 weeks of history
- [ ] Tribunal heatmap showing all 91 courts
- [ ] Recent executions list from GitHub
- [ ] Recent days list from Internet Archive
- [ ] Info section with explanation
- [ ] Responsive layout (mobile, tablet, desktop)
- [ ] Auto-refresh every 5 minutes
- [ ] Loading skeletons
- [ ] Error handling (graceful degradation)

### 10.2 Should Have

- [ ] Hover tooltips on calendar and tribunal cells
- [ ] Click-through to external resources
- [ ] localStorage caching
- [ ] Smooth animations and transitions

### 10.3 Nice to Have

- [ ] Manual refresh button
- [ ] Keyboard navigation
- [ ] Print-friendly view
- [ ] PWA support (offline indicator)

---

## 11. Deliverables

1. **Astro project** — Complete source code with:
   - Configured `astro.config.mjs` with Tailwind and React/Svelte
   - All static components (`.astro` files)
   - All island components (`.tsx` or `.svelte` files)
   - Shared utilities (`lib/`)
   - Tailwind config with design system colors

2. **GitHub Actions workflow** — Auto-deploy to GitHub Pages on push

3. **README** — Setup, development, and deployment instructions

4. **Design assets** — If custom icons/graphics created (favicon, OG image)

---

## 12. Reference Implementation

A working **vanilla JS prototype** is available:

- **File:** `causaganha-dashboard.html`
- **Preview:** Open locally in browser

This prototype demonstrates all core functionality and visual design. It serves as:

- Visual reference for the designer
- Functional reference for the developers
- Proof of concept for API integrations

**Note:** The production Astro version should match this prototype's functionality and visual design, but with cleaner architecture (islands), better performance (selective hydration), and maintainable code structure.

---

## Appendix A: Complete Tribunal List

```
Superiores (6):
STF, STJ, TST, TSE, STM, CNJ

TRFs (6):
TRF1, TRF2, TRF3, TRF4, TRF5, TRF6

TRTs (24):
TRT1, TRT2, TRT3, TRT4, TRT5, TRT6, TRT7, TRT8, TRT9, TRT10,
TRT11, TRT12, TRT13, TRT14, TRT15, TRT16, TRT17, TRT18, TRT19, TRT20,
TRT21, TRT22, TRT23, TRT24

TJs (27):
TJAC, TJAL, TJAM, TJAP, TJBA, TJCE, TJDFT, TJES, TJGO, TJMA,
TJMG, TJMS, TJMT, TJPA, TJPB, TJPE, TJPI, TJPR, TJRJ, TJRN,
TJRO, TJRR, TJRS, TJSC, TJSE, TJSP, TJTO

Total: 63 tribunals (some TRTs may be inactive)
```

## Appendix B: API Response Examples

### Internet Archive — Full Response

```json
{
  "item_size": 710850085,
  "files_count": 51,
  "metadata": {
    "identifier": "djen-2026-01-28",
    "collection": "opensource",
    "creator": "CausaGanha",
    "date": "2026-01-28",
    "description": "Diario de Justica Eletronico Nacional...",
    "mediatype": "data",
    "title": "DJEN Data - 2026-01-28"
  },
  "files": [
    {
      "name": "djen-2026-01-28-TJSP.zip",
      "source": "original",
      "size": "121396165",
      "md5": "ca97dd976e88d0690bd17c40d6525c8f",
      "format": "ZIP",
      "filecount": "225"
    },
    {
      "name": "djen-2026-01-28-STF.absent",
      "source": "original",
      "size": "32",
      "format": "Unknown"
    }
  ]
}
```

### GitHub Actions — Full Response

```json
{
  "total_count": 5209,
  "workflow_runs": [
    {
      "id": 21463186936,
      "name": "Data Pipeline",
      "run_number": 1110,
      "status": "completed",
      "conclusion": "success",
      "created_at": "2026-01-29T02:22:53Z",
      "updated_at": "2026-01-29T02:22:54Z",
      "html_url": "https://github.com/franklinbaldo/causaganha/actions/runs/21463186936",
      "head_commit": {
        "message": "Fix collection script"
      }
    }
  ]
}
```

---

*End of Specification*
