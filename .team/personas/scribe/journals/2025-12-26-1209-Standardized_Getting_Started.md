---
title: "✍️ Standardized Getting Started Guide"
date: 2025-12-26
author: "Scribe"
emoji: "✍️"
type: journal
---

## ✍️ 2025-12-26 - Summary

**Observation:** The `README.md` and `docs/getting-started/quickstart.md` had conflicting installation and usage instructions. The `README.md` used `uv tool install`, while the quickstart guide used the more complex `uvx` command. This inconsistency could confuse new users.

**Action:** I standardized the documentation to use the `uv tool install` method across all guides. I updated `docs/getting-started/quickstart.md` to remove the `uvx` commands and reflect the simpler, more direct `egregora` command usage. I also added a "Quick Start" link to the main navigation in `mkdocs.yml` to make the guide more discoverable.

**Reflection:** This change improves the getting-started experience. However, the high number of failing tests indicates a larger health issue with the codebase. While my changes were scoped to documentation, the next Scribe session should investigate if these test failures are caused by outdated documentation or code examples in other parts of the repository. A healthy codebase requires that documentation and tests are aligned.
