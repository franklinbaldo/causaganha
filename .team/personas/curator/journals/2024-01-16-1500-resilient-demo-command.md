---
title: "🎭 Resilient Demo Command and Navigation Fix"
date: 2024-01-16
author: "Curator"
emoji: "🎭"
type: journal
---

## 🎭 2024-01-16 - Resilient Demo Command and Navigation Fix

**Observation:**
My initial attempts to run the Curation Cycle were blocked by the `egregora demo` command failing prematurely due to API rate limit errors. This left the demo site in an incomplete state, preventing any UX evaluation. Additionally, I identified a long-standing bug where the "Media" navigation link was broken.

**Action:**
1.  I modified the `egregora demo` command in `src/egregora/cli/main.py` to handle the `AllModelsExhaustedError` gracefully. The command now catches this exception, prints a warning message, and proceeds to scaffold a complete "empty state" of the demo site.
2.  I updated the exception handling in `src/egregora/orchestration/pipelines/write.py` to ensure the `AllModelsExhaustedError` is re-raised, allowing the `demo` command to catch it.
3.  I fixed the broken "Media" navigation link in the `src/egregora/rendering/templates/site/mkdocs.yml.jinja` template.
4.  I created a new task, `.../20240116-1500-ux-make-demo-command-resilient.md`, to document the need for this resilience, which is now resolved.

**Reflection:**
A resilient demo command is crucial for maintaining a smooth and efficient Curation Cycle. The principle of "Graceful Degradation" is key here; the system should always produce a usable, even if incomplete, output. This unblocks development and evaluation, even when external dependencies are unavailable. The navigation fix, while a small change, significantly improves the user experience.
