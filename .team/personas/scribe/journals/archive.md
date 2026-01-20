---
title: "✍️ Historical Archive"
date: 2025-05-15
author: "Scribe"
emoji: "✍️"
type: journal
---

# Scribe's Journal

## 2025-05-15 - Missing Plugins & Broken Links
**Confusion:** The README instructed users to run a preview command that failed because it was missing the required `mkdocs-blogging-plugin`. It also pointed to a configuration file path that didn't exist (`docs/configuration.md`), leading to a 404.
**Discovery:** The actual configuration documentation lives at `docs/getting-started/configuration.md`. The `mkdocs-blogging-plugin` is a mandatory dependency for the site build process as per project memory.
**Resolution:** Updated `README.md` to include the missing plugin in the `uvx` command and corrected the link to the configuration guide.

## 2025-05-15 - Protocol Drift & Broken Links
**Confusion:** `docs/architecture/protocols.md` referenced the legacy `OutputAdapter` as a protocol and pointed to non-existent API docs.
**Discovery:** The actual protocol is `OutputSink` in `src/egregora/data_primitives/protocols.py`, and `InputAdapter` is an ABC in `src/egregora/input_adapters/base.py`.
**Resolution:** Updated `docs/architecture/protocols.md` to match the codebase and removed dead links.

## 2025-05-16 - Broken Installation Instructions & Quickstart Dependencies
**Confusion:** `docs/getting-started/installation.md` instructed users to run `uv sync --extra docs`, which doesn't exist. `docs/getting-started/quickstart.md` was missing required MkDocs plugins in the `uvx` command, causing local preview to fail.
**Discovery:** The correct extra is `dev` (which contains MkDocs plugins). The `quickstart.md` command was missing `mkdocs-macros-plugin`, `mkdocs-rss-plugin`, and `mkdocs-glightbox`.
**Resolution:** Corrected the installation instruction to use `--extra dev` (or reliance on dev dependencies) and updated the quickstart `uvx` command to include all necessary plugins.

## 2025-05-18 - Broken Internal Documentation Links
**Confusion:** `docs/reference.md` and several guides contained broken links to non-existent sections (`api/orchestration`, `development/structure.md`, etc.), causing build warnings and dead ends for users.
**Discovery:** The documentation structure had drifted from the actual file layout. Many "development" docs were missing or had been consolidated into `guide/architecture.md` or the root `CONTRIBUTING.md`.
**Resolution:** Updated `docs/reference.md`, `docs/guide/architecture.md`, `docs/guide/generation.md`, and `docs/guide/privacy.md` to point to existing files or external GitHub resources where appropriate.
