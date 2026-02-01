---
title: "✍️ Docs Consistency"
date: 2025-12-25
author: "Scribe"
emoji: "✍️"
type: journal
---

## ✍️ 2025-12-25 - Summary

**Observation:** I identified several inconsistencies across the documentation that could confuse new users. The `README.md`, `docs/getting-started/quickstart.md`, and `docs/getting-started/installation.md` files had different setup and preview commands. Additionally, some links were either broken due to incorrect relative paths or were pointing to outdated V2 documentation.

**Action:** I standardized all setup commands to `uv sync --all-extras` and preview commands to `uv run mkdocs serve -f .egregora/mkdocs.yml`. I also corrected a file structure diagram in `quickstart.md` to show the accurate location of `mkdocs.yml`. I fixed the broken links in the `README.md` and updated the links in `quickstart.md` to point to the relevant V3 documentation.

**Reflection:** While these fixes improve consistency, a more systematic review of all documentation is needed to ensure every link and command is up-to-date. Future sessions should focus on creating a single source of truth for commands, perhaps using includes, to prevent this kind of drift. It would also be beneficial to add a link checker to the CI pipeline to automatically catch broken links.
