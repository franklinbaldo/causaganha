---
id: "20260110-1000-ux-comprehensive-improvements"
title: "Implement 'The Portal' UX Vision"
status: "todo"
author: "curator"
priority: "high"
tags: ["#ux", "#bug", "#design", "#frontend", "#a11y"]
created: "2026-01-10"
updated: "2026-01-11"
---

## 🎭 Curator's Report: Implement "The Portal" UX Vision

This task consolidates the foundational technical fixes required to implement the "Portal" UX vision as defined in `docs/ux-vision.md`. The goal is to resolve the inconsistencies between the site's configuration and its custom styling, and to fix critical bugs that degrade the user experience.

### 🔴 RED: The Problems

1.  **Inconsistent Color Palette:** The `mkdocs.yml` specifies the default `teal` and `amber` colors, which directly conflicts with the dark, immersive theme defined in `extra.css`. The site is not rendering as designed.
2.  **Broken Social Card Images:** The `mkdocs build` process generates 404 errors for social card preview images, making social media sharing look broken.
3.  **Missing Favicon:** The site lacks a favicon, which is a basic element of professional presentation.
4.  **Placeholder Analytics:** The `mkdocs.yml` contains a non-functional placeholder for Google Analytics, which violates our "Privacy-First" principle.

### 🟢 GREEN: Definition of Done

1.  **Color Palette:** The `palette` section in the generated `mkdocs.yml` is updated. The `primary` color is set to `custom` and the accent is removed, allowing `extra.css` to take full control of the color scheme.
2.  **Social Cards:** The `mkdocs build` command completes without any 404 errors related to social card images.
3.  **Favicon:** A placeholder favicon is created and correctly configured in the `mkdocs.yml` theme settings.
4.  **Analytics:** The `extra.analytics` section is completely removed from the `mkdocs.yml` template.

### 🔵 REFACTOR: How to Implement

All changes must be made to the source template in `src/egregora/output_sinks/mkdocs/scaffolding.py`. **Do not edit the `demo/` directory directly.**

1.  **Color Palette:**
    -   In the `MKDOCS_YML_TEMPLATE` string, locate the `theme.palette` section.
    -   Change `primary: teal` to `primary: custom`.
    -   Change `accent: amber` to `accent: yellow` for both light and dark schemes. This ensures consistency with the vision document.

2.  **Analytics:**
    -   In the `MKDOCS_YML_TEMPLATE` string, find and completely delete the `extra.analytics` section.

3.  **Favicon:**
    -   In the `MKDOCS_YML_TEMPLATE` string, add a `favicon` key under the `theme` section, pointing to `assets/images/favicon.png`.
    -   You will need to create a simple placeholder PNG image for the favicon. A 128x128px solid color square is sufficient for now.
    -   Ensure the scaffolding process copies this new favicon to the correct `assets/images` directory in the generated site.

4.  **Social Cards:**
    -   Investigate the `social` plugin configuration in `mkdocs.yml` and the build logs to identify the root cause of the 404 errors. This is a debugging task and may require inspecting the plugin's behavior or the file paths it expects.

### 📍 Where to Look

-   **Primary Target File:** `src/egregora/output_sinks/mkdocs/scaffolding.py`
-   **Reference Vision:** `docs/ux-vision.md`
-   **Build Command for Verification:** `cd demo && uv run mkdocs build -f .egregora/mkdocs.yml`
