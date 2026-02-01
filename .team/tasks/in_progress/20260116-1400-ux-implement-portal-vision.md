---
title: "Implement 'The Portal' UX Vision & Fix Dev Experience"
id: ux-portal-vision-and-dx-fix
author: curator
status: todo
created: 2026-01-16
tags:
  - ux
  - dx
  - frontend
  - bug
  - high-priority
---

## 1. Why: The Problem

The user experience (UX) and developer experience (DX) of the generated MkDocs site are currently broken and inconsistent with the "Portal" vision defined in `docs/ux-vision.md`.

-   **Poor Developer Experience:** The project is unusable out-of-the-box. Running `uv run egregora demo` and `uv run mkdocs build` fails due to a large number of missing dependencies in `pyproject.toml`. This prevents any development or evaluation of the generated site.
-   **Inconsistent Branding:** The site's color scheme is broken. The accent color is hardcoded to `yellow` in the generated `mkdocs.yml`, which conflicts with the dark, immersive "Portal" theme defined in `extra.css`.
-   **Broken Core Features:** Key MkDocs features are non-functional. The social card previews are broken (generating 404 errors during build), and the site is missing a favicon, making it look unprofessional.

## 2. What: The Solution

This task is to fix the foundational issues to align the generated site with the "Portal" UX vision and make the developer experience smooth and reliable.

### 2.1. Fix the Developer Experience (DX)
-   Add all missing dependencies to `pyproject.toml` to ensure `uv run egregora demo` and `uv run mkdocs build` work without errors after a fresh `uv sync`.

### 2.2. Implement the "Portal" Color Scheme
-   Modify the `mkdocs.yml` template to correctly set the theme's accent color to `custom`, allowing `extra.css` to control the palette.

### 2.3. Fix Broken Social Cards
-   Ensure the social card feature is correctly configured and that the necessary dependencies are installed so that images are generated successfully during the build process.

### 2.4. Add a Favicon
-   Add a placeholder favicon to the project and ensure it is copied to the correct location (`demo/docs/assets/images/favicon.png`) during the scaffolding process.

## 3. How: Implementation Details

### 3.1. Update `pyproject.toml`
-   **Where:** `pyproject.toml`
-   **Action:** Add the following dependencies to the `[project.dependencies]` section.
    ```toml
    # Add these packages
    "google-generativeai"
    "ibis-framework[duckdb]"
    "pydantic-ai"
    "ratelimit"
    "lancedb"
    "Pillow"
    "mkdocs-material[imaging]"
    "mkdocs-glightbox"
    ```
-   **Verification:** After adding, run `uv sync` in a clean environment, then confirm `uv run egregora demo` runs without `ModuleNotFoundError`.

### 3.2. Fix Accent Color
-   **Where:** `src/egregora/output_sinks/mkdocs/scaffolding.py`
-   **Action:** Locate the `MKDOCS_YML_TEMPLATE` multiline string. Find the `palette` section and change `accent: yellow` to `accent: custom` under both the `light` and `dark` mode schemes.
-   **Verification:** After the change, run `uv run egregora demo` and inspect `demo/.egregora/mkdocs.yml` to confirm `accent: custom` is present.

### 3.3. Fix Social Cards
-   **Where:** `src/egregora/output_sinks/mkdocs/scaffolding.py`
-   **Action:** In the `MKDOCS_YML_TEMPLATE`, find the `theme.features` list. Add the `cards` feature if it's not already enabled. The `mkdocs-material[imaging]` dependency added in step 3.1 is also required for this to work.
-   **Verification:** Run `cd demo && uv run mkdocs build -f .egregora/mkdocs.yml` and check the build log. There should be no `404` errors related to social card images.

### 3.4. Add Favicon
-   **Action:**
    1.  Create a placeholder 32x32 PNG favicon. You can generate one online or use a simple colored square.
    2.  Save it to a new directory: `src/egregora/output_sinks/mkdocs/scaffold_files/assets/images/favicon.png`.
    3.  Modify `src/egregora/output_sinks/mkdocs/scaffolding.py` to ensure this file is copied to `demo/docs/assets/images/favicon.png` when `egregora demo` is run. The logic for copying the `overrides` directory can likely be adapted.
-   **Verification:** Run `uv run egregora demo` and verify that `demo/docs/assets/images/favicon.png` exists.

## 4. Acceptance Criteria

-   [ ] A developer can clone the repository, run `uv sync`, and then successfully run `uv run egregora demo` without any dependency-related errors.
-   [ ] The generated `demo/.egregora/mkdocs.yml` file contains `accent: custom` for both color schemes.
-   [ ] Running `cd demo && uv run mkdocs build -f .egregora/mkdocs.yml` completes without any 404 errors in the build log related to social cards.
-   [ ] The `demo/docs/assets/images/favicon.png` file exists after running `egregora demo`.
