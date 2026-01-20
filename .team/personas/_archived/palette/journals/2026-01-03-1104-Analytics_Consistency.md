---
title: "🎨 Analytics Consistency"
date: "2026-01-03"
author: "Palette"
emoji: "🎨"
type: journal
---

## 🎨 2026-01-03 - Summary

**Observation:** I identified a functional inconsistency where the main documentation site included a user feedback widget (`extra.analytics`), but this was missing from the user-generated blog template in `src/egregora/rendering/templates/site/mkdocs.yml.jinja`.

**Action:** I updated the `mkdocs.yml.jinja` template to include the missing `extra.analytics` block, copying it from the root `mkdocs.yml`. This brings the blog template to feature parity with the main documentation site, ensuring a consistent user experience.

**Reflection:** This session continues to highlight the issue of configuration drift between the main site and the blog template. A future improvement would be to establish a single source of truth for the MkDocs configuration, perhaps using MkDocs' built-in inheritance (`!include`) or a shared YAML file, to ensure that both the documentation and user blogs inherit from the same base. This would prevent future inconsistencies and strengthen the design system.
