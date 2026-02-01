---
title: "🎭 Fix CSS Fragmentation"
date: 2026-01-29
author: "Curator"
emoji: "🎭"
type: task
tags:
  - ux
  - frontend
  - css
---

## 🎭 Fix CSS Fragmentation

**Observation:**
The project currently has two competing CSS files:
1.  `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`: Contains the "Portal" theme styles (Colors, Glassmorphism, Hero).
2.  `src/egregora/rendering/templates/site/overrides/stylesheets/extra.css`: Contains structural layout improvements (Readability, Related Posts).

Currently, `mkdocs.yml` loads `stylesheets/extra.css`. Because the file exists in `docs/`, it shadows the one in `overrides/`. This means the site has the correct *look* (colors) but is missing the *layout fixes* (related posts styling is broken).

**Objective:**
Consolidate these into a single file in `overrides/` to ensure BOTH theme and layout styles are applied.

### 1. Merge CSS Files
**Scenario: Consolidate Styles**
*   **Given** we have two fragmented CSS files
*   **When** we run the consolidation
*   **Then** `overrides/stylesheets/extra.css` should contain the content of BOTH files.
*   **And** `docs/stylesheets/extra.css` should be deleted.

**Action:**
1.  Read the content of `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`.
2.  Read the content of `src/egregora/rendering/templates/site/overrides/stylesheets/extra.css`.
3.  **Prepend** the content of the `docs` file to the `overrides` file.
    *   *Critical:* Ensure `@import` statements from the `docs` file remain at the very top of the combined file.
4.  Delete `src/egregora/rendering/templates/site/docs/stylesheets/extra.css`.

### 2. Verification
**Scenario: Verify Combined Styles**
*   **Given** the files are merged and `docs/` file is deleted
*   **When** `egregora demo` is run
*   **Then** `demo/overrides/stylesheets/extra.css` should exist.
*   **And** `demo/docs/stylesheets/extra.css` should NOT exist.
*   **And** the generated `extra.css` should contain both `.homepage-hero` (from Portal theme) AND `.related-posts` (from Layout fixes).

**Verification:**
1.  Run `egregora demo`.
2.  Inspect `demo/overrides/stylesheets/extra.css`.
3.  Search for `.homepage-hero` (should be present).
4.  Search for `.related-posts` (should be present).
