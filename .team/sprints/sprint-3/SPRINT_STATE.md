# Sprint 3 - Final State

**Owner:** Maintainer
**Date:** 2026-01-16
**Status:** Planned

## Top Goals (ordered)
1. **Security Hardening & Safety:** Complete the security test suite to cover all OWASP Top 10 vulnerabilities, ensuring a robust defensive posture. (Sentinel)
2. **Codebase Health & Data Integrity:** Enforce strict data schemas at system boundaries and eliminate technical debt to prevent runtime errors. (Artisan, Refactor)
3. **Strategic Alignment & Vision:** Analyze initial data streams and formalize the decision on the "Egregora Symbiote" architecture. (Steward, Visionary)

## Commitments (Scope Locked)
- **Sentinel:**
  - **Deliverable:** Comprehensive security tests for OWASP categories A04, A07, A08, A09, and A10.
  - **Acceptance Criteria:** Tests exist in `tests/security/` and pass in the CI pipeline.
- **Artisan:**
  - **Deliverable:** Implementation of a DataFrame schema (e.g., using Pandera) for at least one core data structure.
  - **Deliverable:** Refactoring of one Input Adapter and decomposition of one "God Class".
  - **Acceptance Criteria:** Code passes strict type checks and the new schema validation enforces data integrity.
- **Refactor:**
  - **Deliverable:** Elimination of all remaining `vulture` and `ruff` warnings.
  - **Deliverable:** A comprehensive review document of the current test suite.
  - **Acceptance Criteria:** Pre-commit hooks for linting pass cleanly; review document is published.
- **Steward:**
  - **Deliverable:** Formal ADR deciding the future of the "Egregora Symbiote".
  - **Deliverable:** Updated project roadmap and Sprint 3 kick-off communication.
  - **Acceptance Criteria:** ADR is merged into `.team/adr/` and approved by the team.
- **Visionary:**
  - **Deliverable:** Analysis report on the "Structured Data Sidecar" output.
  - **Deliverable:** "Friction Hunting" report identifying the next major opportunity.
  - **Acceptance Criteria:** Reports are published to `.team/notes/` or the wiki.
- **Curator:**
  - **Deliverable:** Accessibility Audit Report (automated/manual).
  - **Deliverable:** Design specifications for Typography and Navigation structure.
  - **Acceptance Criteria:** Specifications are documented; Audit report includes actionable JIRA/GitHub tasks.

## Deferred Items
- **Visionary's Real-time Adapter Prototype:** Deferred due to the absence of `Builder` and `Architect` personas required for implementation and architectural alignment.
- **Visionary's "Related Concepts API" RFC:** Deferred pending architectural review.
- **Curator's "Related Content" Implementation:** Deferred due to the absence of the `Forge` persona.
- **Curator's Navigation Restructuring (Implementation):** Deferred due to the absence of the `Forge` persona.

## Dependencies & Sequencing
- **[CRITICAL] `Sentinel` Independent Execution:** Sentinel's work is self-contained and should proceed immediately to improve security posture.
- **[RISK] `Artisan` <> `Architect`:** Artisan intends to consult Architect on schema libraries. Since Architect is not scheduled, Artisan must make a provisional decision and document the trade-offs in an ADR.
- **[RISK] `Curator` <> `Forge`:** Curator's implementation goals are strictly blocked. Curator must focus entirely on design specifications and audits to prepare work for Forge in the next sprint.

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing `Forge`, `Builder`, `Architect` blocks implementation | High | Affected tasks have been explicitly deferred. Maintainer will vote to include these personas in the next sprint. |
| Artisan chooses a schema library that conflicts with future architecture | Medium | Artisan will document the decision in an ADR to allow for future review. |
| Curator runs out of non-implementation work | Low | Curator can expand the scope of the Accessibility Audit or deeper UX research. |

## Persona Governance
The absence of `Forge`, `Builder`, and `Architect` continues to be a bottleneck for "Visionary" and "Curator" initiatives. The sequence vote for Sprint 4 MUST prioritize these personas to unlock the backlog of designs and specifications.
