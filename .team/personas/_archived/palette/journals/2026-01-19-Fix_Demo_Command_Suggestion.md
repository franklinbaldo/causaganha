## 🎨 2026-01-19 - Fix Demo Command Suggestion

**Observation:** I noticed that the `egregora demo` and `egregora init` commands suggest running `mkdocs serve` with `uv tool run --with mkdocs-material ...` but omit the `[imaging]` extra. This causes the build to fail or emit warnings about missing `cairosvg` and `PIL` dependencies, breaking the social card generation feature which is a core part of the "Portal" UX vision.

**Action:** I updated the command suggestions in `src/egregora/cli/main.py` to include `mkdocs-material[imaging]`. This ensures that when users copy-paste the suggested command, the necessary dependencies for social card generation are installed in the ephemeral environment.

**Reflection:** This was a small but critical "Micro-UX" fix. A broken copy-paste command is a major friction point for new users. By ensuring the suggested command works out-of-the-box and supports all features (like social cards), we improve the first-run experience significantly. The task `20260116-1400-ux-implement-portal-vision` had multiple components, but most were already resolved in the codebase; this was the remaining gap.
