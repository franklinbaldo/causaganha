---
title: "🎭 Refine Portal Theme Scoping and Navigation"
date: 2026-01-22
author: "Curator"
emoji: "🎭"
type: task
---

## 🎭 Refine Portal Theme Scoping and Navigation

**Observation:**
The "Portal" theme currently applies aggressive global CSS overrides in `extra.css` that degrade usability on standard content pages. Specifically, it globally hides the Table of Contents (TOC) and the page title (H1). Additionally, the navigation structure and hardcoded URLs in `mkdocs.yml` need refinement.

**Context:**
The "Portal" theme is designed to be immersive, but this immersion should not come at the cost of basic usability for documentation and long-form content. We need to scope our visual overrides carefully.

**Objectives:**

### 1. Scope CSS Overrides
**Scenario: Restore Standard Page Usability**
*   **Given** the current `extra.css` hides `.md-sidebar--secondary` (TOC) and H1 globally
*   **When** a user visits a standard page (About, Blog Post, etc.)
*   **Then** the Table of Contents should be visible.
*   **And** the Page Title (H1) should be visible.

**Action:**
*   Remove `.md-sidebar--secondary { display: none !important; }` from `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`.
*   Remove `.md-main__inner>.md-content>.md-content__inner>h1 { display: none !important; }` from `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`.

### 2. Update Homepage Configuration
**Scenario: Homepage Cleanliness**
*   **Given** we removed the global CSS hiding TOC
*   **When** the Homepage (`index.md`) is rendered
*   **Then** it should still NOT show a Table of Contents.

**Action:**
*   Update `src/egregora/rendering/templates/site/docs/index.md.jinja` to include frontmatter:
    ```yaml
    ---
    hide:
      - navigation
      - toc
    ---
    ```
    (Note: `navigation` hiding is optional depending on design preference, but `toc` hiding is required here to replace the CSS hack).

### 3. Refine Navigation & Config
**Scenario: Navigation Structure**
*   **Given** "Media" is currently a top-level navigation item
*   **When** the site is built
*   **Then** the navigation should be clear and logical.
*   **And** the `site_url` should not be hardcoded to localhost if possible, or at least commented as such.

**Action:**
*   Update `src/egregora/rendering/templates/site/mkdocs.yml.jinja`:
    *   Ensure `site_url` uses the `site_url` variable correctly or defaults safely.
    *   (Optional) Move "Media" under a "Resources" tab if desired, or leave as is but verify the path.

**Verification:**
1.  Run `egregora demo`.
2.  Serve the site (or inspect the files).
3.  Verify `index.md` has the `hide: - toc` frontmatter.
4.  Verify `extra.css` no longer has the global `display: none` for sidebars and H1s.
5.  Verify standard pages (like `about.md`) show a TOC (if they have headers).
