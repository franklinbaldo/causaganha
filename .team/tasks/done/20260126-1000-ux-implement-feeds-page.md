# UX Task: Implement Feeds Page to Fix 404

**Status**: TODO
**Created**: 2026-01-26
**Priority**: High (Fixes Broken Link on Homepage)
**Assignee**: Forge

## Context
The homepage contains a "Quick Navigation" card for "RSS Feeds" that links to `feeds/`. Currently, this page does not exist in the generated site, resulting in a 404 error. The `mkdocs-rss-plugin` generates XML/JSON feed files, but provides no user-facing index page.

The template for this page already exists in the source, but it is not being rendered by the scaffolding logic.

## Requirements

### 1. Verify Template Exists
Confirm the existence of `src/egregora/rendering/templates/site/docs/feeds/index.md.jinja`.
It should contain the "Subscribe to Updates" content and glassmorphism card grid.
(Do not overwrite if it exists and looks correct).

### 2. Update Scaffolding
Update `src/egregora/output_sinks/mkdocs/scaffolding.py` to register the template so it is generated during site creation.

**Action:**
1.  Open `src/egregora/output_sinks/mkdocs/scaffolding.py`.
2.  Locate the `templates_to_render` list in the `_create_template_files` method.
3.  Add the following entry:
    ```python
    (docs_dir / "feeds" / "index.md", "docs/feeds/index.md.jinja"),
    ```
4.  Verify that directory creation handles nested paths (it should, as `target_path.parent.mkdir` is called).

## Verification
1.  Run `egregora demo` (or `uv run egregora demo`).
2.  Verify `demo/docs/feeds/index.md` is created.
3.  Serve the site and click "RSS Feeds" on the homepage. It should load the new page successfully.
