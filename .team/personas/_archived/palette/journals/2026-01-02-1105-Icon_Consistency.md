---
title: "🎨 Icon Consistency"
date: 2026-01-02
author: "Palette"
emoji: "🎨"
type: journal
---

## 🎨 2026-01-02 - Summary

**Observation:** I identified a visual and functional inconsistency where the main documentation site defined `theme.icon` configurations for repository, edit, and view links, but the user-generated blog template in `src/egregora/rendering/templates/site/mkdocs.yml.jinja` was missing this block entirely. This resulted in a less functional UI for the blogs.

**Action:** I updated the `mkdocs.yml.jinja` template to include the missing `theme.icon` block, copying it directly from the root `mkdocs.yml`. This ensures that all generated blogs will have the same helpful icons as the main documentation site, creating a consistent user experience.

**Reflection:** This session continues to highlight the issue of configuration drift between the main site and the blog template. A future improvement would be to establish a single source of truth for the MkDocs configuration, perhaps using MkDocs' built-in inheritance (`!include`) or a shared YAML file, to ensure that both the documentation and user blogs inherit from the same base. This would prevent future inconsistencies and strengthen the design system.
