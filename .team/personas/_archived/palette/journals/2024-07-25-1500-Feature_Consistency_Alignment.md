---
title: "🎨 Align MkDocs UX Features for Consistency"
date: 2024-07-25
author: "Palette"
emoji: "🎨"
type: journal
---

## 🎨 2024-07-25 - Summary

**Observation:** I identified a functional inconsistency between the project's documentation site and the theme for user-generated blogs. The root `mkdocs.yml` enabled a rich set of user experience features (like instant navigation, code annotation, and table of contents tracking) that were missing from the blog template in `src/egregora/rendering/templates/site/mkdocs.yml.jinja`.

**Action:** I updated the `features` section in the `mkdocs.yml.jinja` template to mirror the comprehensive configuration of the root `mkdocs.yml`. This ensures that all generated blogs will have the same high-quality, polished user experience as the main documentation site.

**Reflection:** The project's design system tokens (colors, fonts) are consistent, but this session revealed a gap in functional features. The root and template configurations are managed in separate files, leading to drift. A future improvement would be to establish a single source of truth for the MkDocs configuration, perhaps using MkDocs' built-in inheritance (`!include`) or a shared YAML file, to ensure that both the documentation and user blogs inherit from the same base. This would prevent future inconsistencies and strengthen the design system.