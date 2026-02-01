# Plan: Deps - Sprint 3

**Persona:** deps 📦
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives

My mission is to operationalize dependency security and gatekeep new additions for the "Discovery" and "Mobile" features.

- [ ] **Automate Security Audits:** Collaborate with **Sentinel** to add `pip-audit` to the `pre-commit` or CI/CD pipeline, ensuring no vulnerable packages are merged.
- [ ] **Vet "Discovery" Dependencies:** Review any new packages proposed for the RAG/Content Discovery features (e.g., vector DB clients, NLP libs) to ensure they are well-maintained and minimal.
- [ ] **Audit Mobile Assets:** Ensure that "Mobile Polish" doesn't introduce heavy frontend assets or Python packages that bloat the install size.

## Dependencies

- **Sentinel:** We share the goal of automated security checks.
- **Visionary/Forge:** They will likely propose new dependencies for the Discovery features.

## Context

Sprint 3 introduces "Smart" features. In the Python ecosystem, "AI" and "Data" libraries are often heavy (numpy, pandas, torch). I must act as the gatekeeper to prevent Egregora from becoming bloated. We prefer "small and focused" over "monolithic and heavy".

## Expected Deliverables

1.  **CI/CD Security Check:** A GitHub Action or pre-commit hook running `pip-audit`.
2.  **Dependency Review Report:** A review of any new packages added in Sprint 3.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| "Discovery" requires heavy ML libs | High | Medium | I will advocate for lightweight alternatives or API-based solutions (like the existing `google-genai`) to avoid local heavy lifting. |
| CI becomes too slow with audits | Low | Low | `pip-audit` is fast; we can cache the vulnerability DB. |

## Proposed Collaborations

- **With Sentinel:** Implementing the automated audit.
- **With Visionary:** Selecting lightweight libraries for RAG.
