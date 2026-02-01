# Plan: Sentinel - Sprint 2

**Persona:** Sentinel 🛡️
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** High

## Objectives
My mission is to ensure security is "built-in" to the new structural changes (ADRs, Config Refactor) and to maintain a clean vulnerability slate.

- [ ] **Secure Configuration Refactor:** Collaborate with Artisan to ensure the new Pydantic configuration uses `pydantic.SecretStr` for sensitive data and validates input strictly.
- [ ] **Security in ADRs:** Work with Steward to embed a mandatory "Security Implications" section into the new ADR template and review initial ADRs.
- [ ] **Patch Vulnerabilities:** Upgrade `protobuf` to fix CVE-2026-0994 and verify no regressions.
- [ ] **Audit Runner Refactor:** Review Artisan's decomposition of `runner.py` to ensure security contexts (e.g., rate limits, blocklists) are preserved during the refactor.
- [ ] **OWASP Test Suite Expansion:** Add tests for A05 (Security Misconfiguration) specifically targeting the new configuration loading logic.

## Dependencies
- **Artisan:** My work on configuration security is directly tied to their Pydantic refactor.
- **Visionary:** I need access to the `GitHistoryResolver` prototype to audit it.
- **Steward:** I need the ADR template to be available to provide feedback.

## Context
Sprint 2 is a "Structure" sprint. The team is hardening the foundation. This is the perfect time to embed security into the DNA of the project (via Config and ADRs) before we start building complex new features in Sprint 3.

## Expected Deliverables
1.  **Secured Pydantic Models:** `SecretStr` usage in `src/egregora/config/`.
2.  **Updated ADR Template:** Template with security section.
3.  **Patched Dependencies:** `protobuf` updated in `pyproject.toml`.
4.  **Security Regression Tests:** New tests in `tests/security/` covering configuration and runner logic.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Config Refactor Exposes Secrets | Medium | High | I will pair with Artisan and write tests that attempt to print/log the config object to ensure secrets are masked. |
| Command Injection in Git Tool | High | High | I will enforce `subprocess.run(shell=False)` via code review and potentially a pre-commit hook or test. |
| ADRs Ignore Security | Low | Medium | I will proactively review the template and the first few ADRs. |

## Proposed Collaborations
- **With Artisan:** Close collaboration on `config.py`.
- **With Visionary:** Review of `detect_refs.py` and `resolve_commit.py`.
- **With Steward:** Review of `.team/adr/TEMPLATE.md`.
