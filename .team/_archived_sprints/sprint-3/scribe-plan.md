# Plan: Scribe - Sprint 3

**Persona:** Scribe ✍️
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** High

## Objectives
My mission is to document the "Symbiote Shift" - the integration of the Context Layer (Git History + Code References) into the core workflow.

- [ ] **Document "Discovery" Features:** Create a comprehensive guide on how the Content Ranking and Related Content features work, including how users can configure them (or confirming they are zero-config).
- [ ] **Document Universal Context Layer API (RFC 026):** Create API documentation (likely OpenAPI-based) for the new local API service proposed by **Visionary**.
- [ ] **Chronicle the "Symbiote Era":** Collaborate with **Lore** to update the high-level architecture documentation (`docs/architecture/`) to reflect the shift from "Batch" to "Symbiote" (Sidecar) architecture.
- [ ] **Mobile Documentation Audit:** Perform a full audit of the Egregora documentation site (`mkdocs serve`) on mobile devices. Identify and fix any layout issues, ensuring the docs themselves are "Mobile Polished".
- [ ] **API Reference Generation:** Ensure the new modules introduced in Sprint 2 (`src/egregora/orchestration/pipelines/etl/`, `src/egregora/config/`) have automatically generated API references in the documentation.
- [ ] **Update "Getting Started":** Review and refine the "Getting Started" guide to reflect the "polished" experience, ensuring screenshots and commands are current.

## Dependencies
- **Curator/Forge:** I need the "Discovery" features to be finalized before I can document them accurately.
- **Simplifier:** I need the new ETL package structure to be stable for API doc generation.
- **Visionary:** I need the RFC 026 API spec to be drafted.
- **Lore:** I need the "Batch Era" documentation to be complete before I can write the "Symbiote Era" docs.

## Context
Sprint 3 focuses on "Mobile Polish & Discovery", but also marks the beginning of the "Symbiote Era" with the introduction of the Context Layer API. The documentation must explain *why* this is magic and *how* it benefits them. Additionally, as we polish the mobile experience of the blog, our own documentation site must set the example.

## Expected Deliverables
1.  **"Understanding Discovery" Guide:** A new concept guide in `docs/concepts/`.
2.  **Context Layer API Docs:** `docs/api/context-layer.md`.
3.  **Symbiote Architecture Overview:** Updated `docs/architecture/overview.md`.
4.  **Mobile-Optimized Docs:** Fixes to CSS/Layout of the documentation site.
5.  **Updated API References:** New sections in `docs/reference/`.
6.  **Refined "Getting Started":** Updated text and visuals.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Abstract Concepts Confuse Users | High | High | I will use diagrams and concrete examples (Before/After) to explain the Context Layer. |
| API Docs are Noisy | Medium | Low | I will configure `mkdocstrings` filters to show only public interfaces, hiding internal implementation details. |

## Proposed Collaborations
- **With Visionary:** To accurately describe the intent and mechanics of the Context Layer.
