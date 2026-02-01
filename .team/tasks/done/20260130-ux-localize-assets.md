---
title: "🎭 Localize Assets for Privacy"
date: 2026-01-30
author: "Curator"
emoji: "🎭"
type: task
tags:
  - ux
  - frontend
  - privacy
  - gdpr
---

## 🎭 Localize Assets for Privacy

**Observation:**
The current site configuration violates the "Privacy-First" principle by making default external requests to third-party CDNs.
1.  **Google Fonts:** `extra.css` imports fonts from `fonts.googleapis.com`.
2.  **MathJax:** `mkdocs.yml` loads scripts from `unpkg.com`.

This leaks user IP addresses to these providers without consent.

**Objective:**
Eliminate external requests by bundling assets locally or configuring `mkdocs-material` to handle them privacy-compliantly.

### 1. Localize Fonts
**Scenario: Remove Google Fonts Import**
*   **Given** `src/egregora/rendering/templates/site/overrides/stylesheets/extra.css` contains an `@import` statement for Google Fonts
*   **When** the fix is applied
*   **Then** the `@import` statement should be removed.
*   **And** the fonts (`Outfit` and `Inter`) should be configured in `mkdocs.yml` using `theme.font`.
    *   *Note:* MkDocs Material automatically downloads and bundles fonts defined in `theme.font`.
    *   *Constraint:* Material only supports one `text` and one `code` font easily. If `Outfit` (headings) and `Inter` (body) cannot both be defined via config, prioritize `Inter` for text and find a way to bundle `Outfit` manually (e.g., download WOFF2 files to `assets/fonts/` and use `@font-face` in CSS).
    *   *Preferred Solution:* Use `theme.font` for `Inter`. Manually bundle `Outfit` for headings if necessary.

### 2. Localize MathJax
**Scenario: Remove Unpkg Script**
*   **Given** `src/egregora/rendering/templates/site/mkdocs.yml.jinja` contains `extra_javascript` pointing to `unpkg.com`
*   **When** the fix is applied
*   **Then** the external link should be removed.
*   **And** MathJax should be provided locally OR via a privacy-respecting MkDocs plugin if available.
    *   *Alternative:* If bundling MathJax is too heavy, document that it is removed for privacy reasons and provide instructions for users to re-enable it if needed.
    *   *Decision:* If `mkdocs-material`'s built-in math support (`pymdownx.arithmatex`) works without external scripts (it usually requires MathJax or KaTeX loaded), verify if we can bundle a lightweight KaTeX instead.
    *   *Goal:* No external requests on page load.

### 3. Verification
**Scenario: Verify No External Requests**
*   **Given** the site is generated with `egregora demo`
*   **When** the site is served and inspected
*   **Then** there should be NO network requests to `fonts.googleapis.com`, `fonts.gstatic.com`, or `unpkg.com`.
*   **And** the typography should still look correct (Inter for body, Outfit for headers if possible).

## Resolution
**Date:** 2026-01-31
**By:** Forge ⚒️

Verified that the site configuration is compliant with privacy requirements:
1.  **Fonts:**
    - `Outfit` font is manually bundled in `overrides/assets/fonts/outfit.woff2` and referenced in `extra.css`.
    - `Inter` and `Roboto Mono` are configured in `mkdocs.yml` via `theme.font`. The `privacy` plugin in `mkdocs-material` automatically downloads and bundles these fonts at build time, preventing external requests.
2.  **MathJax:**
    - MathJax scripts are vendored in `overrides/javascripts/` (`mathjax.js` and `tex-mml-chtml.js`).
    - No external requests to `unpkg.com` are made.
3.  **Verification:**
    - Ran `tests/step_defs/test_privacy_steps.py` using Playwright.
    - Confirmed no requests to `fonts.googleapis.com`, `fonts.gstatic.com`, or `unpkg.com`.
    - Confirmed correct font usage (`Outfit` for headers, `Inter` for body).
