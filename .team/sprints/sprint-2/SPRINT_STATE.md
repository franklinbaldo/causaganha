# Sprint 2 - Final State

**Owner:** Maintainer
**Date:** 2024-07-30
**Status:** Planned

## Top Goals (ordered)
1. **Improve Codebase Health & Quality:** Address technical debt and improve code structure through targeted refactoring, type safety enhancements, and cleanup of unused code. (Artisan, Refactor)
2. **Establish Foundational UX & Automation:** Define the core visual identity and refactor the necessary modules to enable automated creation of UX tasks, unblocking future front-end work. (Curator, Refactor)
3. **Build Proactive Security Test Suite:** Begin implementation of an automated security test suite based on the OWASP Top 10 to catch vulnerabilities early. (Sentinel)

## Commitments (Scope Locked)
- **Artisan:**
  - **Deliverable:** Introduce Pydantic models in `config.py` for type-safe configuration.
  - **Acceptance Criteria:** The application configuration is managed through validated Pydantic models.
- **Refactor:**
  - **Deliverable:** Eliminate all `vulture` (unused code) and `check-private-imports` warnings from the codebase.
  - **Acceptance Criteria:** The corresponding pre-commit hooks pass without errors.
- **Refactor & Curator (Joint):**
  - **Deliverable:** Refactor the `issues` module to provide a clear API for automation.
  - **Acceptance Criteria:** The Curator can programmatically create and verify UX-related tasks using the new module API.
- **Curator:**
  - **Deliverable:** Define the primary color palette and typography scale for the blog.
  - **Acceptance Criteria:** The visual identity guidelines are documented in `docs/ux-vision.md`.
- **Sentinel:**
  - **Deliverable:** Implement initial security tests for at least two OWASP Top 10 categories (e.g., Broken Access Control, Injection).
  - **Acceptance Criteria:** New, passing tests exist in the `tests/security/` directory covering these categories.

## Deferred Items
- **Curator's Lighthouse Audit Script:** Deferred as it requires implementation work from the `Forge` persona, who is not scheduled for this sprint.
- **Visionary's "Structured Data Sidecar" Spec:** Deferred as it requires collaboration with the `Architect` and `Builder` personas, who are not scheduled for this sprint. The Visionary should focus on research and drafting RFCs independently for now.

## Dependencies & Sequencing
- **[BLOCKER] `Refactor` -> `Curator`:** The refactoring of the `issues` module by the `Refactor` persona must be prioritized and completed to unblock the `Curator`'s automation goals.
- **`Artisan` <> `Refactor`:** Both personas may be working in core areas. They must communicate their plans for `runner.py` and `utils/` early to avoid merge conflicts.

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| `Refactor` and `Artisan` changes conflict | Medium | Personas are required to communicate plans for shared modules before implementation begins. |
| `issues` module refactor doesn't meet Curator's needs | High | `Curator` must provide clear, written requirements to `Refactor` before work begins. A brief review of the proposed API should be conducted. |
| Key personas (`Forge`, `Architect`, `Builder`) are unavailable | Medium | Work dependent on these personas has been explicitly deferred. If their absence continues, future sprints will be blocked. This will be re-evaluated in the next sprint planning cycle. |

## Persona Governance
No changes to the persona roster this sprint. However, the number of deferred items due to the absence of `Forge`, `Architect`, and `Builder` indicates a potential bottleneck. The effectiveness of the current sprint composition will be re-evaluated at the end of Sprint 2.
