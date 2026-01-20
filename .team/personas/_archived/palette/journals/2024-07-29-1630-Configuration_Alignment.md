---
title: "🎨 Configuration Alignment for Search and Copyright"
date: 2024-07-29
author: "Palette"
emoji: "🎨"
type: journal
---

## 🎨 2024-07-29 - Summary

**Observation:** I identified several minor but impactful inconsistencies between the root `mkdocs.yml` and the `mkdocs.yml.jinja` template for user blogs. The blog template had a less precise search configuration and used a non-standard location for the copyright notice.

**Action:**
1.  **Search Alignment:** I copied the `separator` regex from the main documentation's search configuration to the blog template to improve search precision.
2.  **Copyright Standardization:** I moved the copyright notice from the `extra` block to the top-level `copyright` key in the blog template, aligning it with Material for MkDocs best practices.

**Reflection:** While many major inconsistencies have been resolved in previous sessions, this session highlights that subtle configuration drift is still a problem. The separate management of `mkdocs.yml` and the Jinja template is the root cause. The repeated recommendation to establish a single source of truth for MkDocs configuration (via `!include` or a shared YAML base) remains the most important next step to prevent these issues permanently and solidify the design system.
