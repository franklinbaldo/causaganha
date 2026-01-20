---
title: "🎨 Font Consistency"
date: 2025-12-26
author: "Palette"
emoji: "🎨"
type: journal
---

## 🎨 2025-12-26 - Summary

**Observation:** I noticed a font inconsistency between the project's documentation site and the theme for user-generated blogs. The documentation used `Roboto`, while the blog templates used `Inter`. This created a disjointed brand experience.

**Action:** I modified `src/egregora/rendering/templates/site/mkdocs.yml.jinja` to change the font from `Inter` to `Roboto`, ensuring a consistent and unified visual identity across all project outputs.

**Reflection:** The project's design tokens are not centralized. The theme fonts were defined in two separate `mkdocs.yml` files. A future improvement would be to extract these theme definitions into a central, reusable configuration that both the documentation site and the blog templates can inherit from. This would prevent future inconsistencies and make the design system more robust.
