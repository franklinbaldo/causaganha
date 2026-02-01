# Plan: Sentinel - Sprint 3

**Persona:** Sentinel 🛡️
**Sprint:** 3
**Created:** 2026-01-26 (during Sprint 1)
**Priority:** High

## Objectives
<<<<<<< HEAD
<<<<<<< HEAD
My mission is to prepare the security defenses for the incoming "Symbiote" architecture and Real-Time Adapters.

- [ ] **Threat Model "Real-Time Adapters":** Analyze the RFC from Sprint 2 and produce a Threat Model document identifying risks (SSRF, DoS, Data Exfiltration).
- [ ] **Implement Adapter Sandboxing:** Design and implement the security controls for the new adapter framework (e.g., restricted network access, resource quotas).
- [ ] **Automated Security Gates:** Integrate `pip-audit` and `bandit` explicitly into the new `taskmaster` or CI pipelines.
- [ ] **Secret Rotation Policy:** Establish a documented policy and potential tooling for rotating the API keys used by the new architecture.

## Dependencies
- **Visionary:** I need the "Real-Time Adapter Framework" RFC to be finalized.
- **Simplifier:** I need the new pipeline structure to be stable to integrate automated security gates.

## Context
Sprint 3 is where the "Egregora Symbiote" starts to become real. Moving from a batch-processed static site generator to a real-time, data-ingesting agent significantly increases the risk profile. My focus shifts from "Code Hygiene" to "Architecture Security."

## Expected Deliverables
1.  **Threat Model Document:** `.team/security/threat-models/real-time-adapters.md`.
2.  **Sandboxing Utilities:** Python decorators or context managers for restricted execution in `src/egregora/security/sandbox.py`.
3.  **Security CI Job:** Updated workflow or task definition including security scanners.
=======
>>>>>>> origin/pr/2856
=======
**Created:** 2026-01-25
**Priority:** Medium

## Objectives

My mission is to shift from "Reactive Patching" to "Proactive Assurance" as we scale the new architecture.

- [ ] **Automated Security Gates:** Collaborate with Sheriff to add `pip-audit` and `bandit` as blocking steps in the CI pipeline (GitHub Actions).
- [ ] **Fuzz Testing Prototype:** Implement a basic fuzzing harness (using `atheris` or `python-afl`) for the `GitHistoryResolver` and `CodeReferenceDetector` to ensure robustness against malformed inputs.
- [ ] **Content Security Policy (CSP) Definition:** Define a strict CSP for the generated static sites to prevent XSS even if HTML injection occurs.
- [ ] **Third-Party Review:** Conduct a manual review of any new dependencies introduced in Sprint 2/3.

## Dependencies

- **Sheriff:** I need access/collaboration on the CI/CD workflows (`.github/workflows/`).
- **Visionary:** I need the `CodeReferenceDetector` to be stable enough to fuzz.

## Context

By Sprint 3, the "Structure" (Sprint 2) will be in place. We will likely be adding more complex features. This is the time to automate the security checks so I don't have to run them manually every session. Also, the new "Context" features (Git integration) introduce parsing complexity, which smells like a target for fuzzing.

## Expected Deliverables

1.  **CI Workflow Update:** PR adding security jobs to the build pipeline.
2.  **Fuzz Test Suite:** A new directory `tests/fuzz/` with at least one active fuzzer.
3.  **CSP Header/Meta:** Updates to the HTML templates to include `<meta http-equiv="Content-Security-Policy" ...>`.
>>>>>>> origin/pr/2831

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
<<<<<<< HEAD
<<<<<<< HEAD
| Adapters allow SSRF | High | Critical | I will mandate the use of the `validate_public_url` utility for *all* adapter network requests. |
| New dependencies introduce vulnerabilities | Medium | High | I will enforce `pip-audit` checks on all new PRs. |

## Proposed Collaborations
- **With Visionary:** Reviewing the security implications of the new adapter design.
=======
>>>>>>> origin/pr/2856
=======
| Fuzzing finds nothing | Medium | Low | Good! It proves robustness. I will time-box this activity. |
| CI becomes too slow | Medium | Medium | I will ensure security scans run in parallel or are cached efficiently. |

## Proposed Collaborations

- **With Sheriff:** CI/CD integration.
- **With Forge:** Implementing CSP in templates.
>>>>>>> origin/pr/2831
