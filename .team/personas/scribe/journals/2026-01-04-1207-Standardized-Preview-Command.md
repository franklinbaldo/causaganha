---
title: "✍️ Standardized Preview Command"
date: 2026-01-04
author: "Scribe"
emoji: "✍️"
type: journal
---

## ✍️ 2026-01-04 - Summary

**Observation:** I identified an inconsistency in the command for previewing the documentation site across `README.md`, `docs/getting-started/installation.md`, and `docs/getting-started/quickstart.md`. The existing `uv run mkdocs serve` command would fail for users who installed the tool directly, as it relies on a local developer environment.

**Action:** I standardized the preview command in all three files to use `uv tool run --with mkdocs-material --with mkdocs-blogging-plugin --with mkdocs-macros-plugin --with mkdocs-rss-plugin --with mkdocs-glightbox mkdocs serve -f .egregora/mkdocs.yml`. This command ensures that all necessary dependencies are present, providing a consistent and functional experience for all users.

**Reflection:** The documentation for previewing the site is now consistent. In a future session, I should perform a broader review of the documentation to identify and correct any other command inconsistencies. Implementing a CI job to validate code examples in the documentation would be a valuable addition to prevent such issues in the future.
