# Jules System Evaluation & Improvement Report

> **Note (2026-01-29):** Historical evaluation document. References to Sheriff, Refactor, and legacy scheduler components are outdated. The team now has 21 personas (20 AI + 1 human) using the ROSAV prompt framework. The scheduler has been rewritten as `stateless.py` with round-robin mode.

**Date:** 2026-05-21
**Evaluator:** Jules (Lead Architect Persona)

## 1. Executive Summary

The `.team/` system is a sophisticated agent orchestration engine that effectively manages a "virtual team" of AI personas. The transition to `scheduler_v2.py` (Clean Architecture) is underway but incomplete, leaving significant technical debt in `scheduler_legacy.py`.

The system's greatest strength is its **autonomy**—agents self-schedule, plan sprints, and execute work via PRs. Its greatest weakness is **sequential blocking** in Cycle Mode and **inconsistent abstraction** in the codebase (mixing Git CLI and GitHub API).

This report outlines a plan to finalize the V2 migration, introduce parallel execution tracks, and harden the core infrastructure.

---

## 2. Technical Evaluation

### 2.1 Codebase Health
| Component | Status | Issues |
| :--- | :--- | :--- |
| **Scheduler V2** | 🟡 Partial | Still imports from `scheduler.py` (legacy shim). needs to fully own the domain. |
| **Scheduler Legacy** | 🔴 Critical | massive "god object" containing Sprint logic, Templates, Git wrappers, and legacy execution flow. |
| **API Client** | 🟡 Fair | Uses manual `for` loops for retries instead of robust libraries like `tenacity`. |
| **GitHub Integration** | 🟠 Mixed | Mixes `subprocess.run(["git"...])` and `httpx` API calls. Makes testing/mocking difficult. |
| **Configuration** | 🟢 Good | `schedules.toml` is clear and effective. |

### 2.2 Architecture Gaps
1.  **Circular Dependencies**: `scheduler_v2` -> `scheduler` -> `scheduler_legacy`. This makes refactoring dangerous.
2.  **Implicit State**: Sprint state is managed via text files (`current.txt`), which is simple but fragile during concurrent writes.
3.  **Hardcoded Templates**: Large Jinja2 templates (`IDENTITY_BRANDING`, `JOURNAL_MANAGEMENT`) are defined as global string constants in python files rather than `.j2` resources.

---

## 3. Operational Improvements

### 3.1 Parallelization Strategy
Currently, the **Cycle Mode** is strictly sequential:
`A -> B -> C -> D`

If `B` (e.g., Refactor) takes 30 minutes, `C` (Visionary) waits. Many agents are orthogonal and should run in parallel.

**Recommendation:** Introduce **Tracks** in `schedules.toml`.

```toml
[tracks]
# Core Product Track (Sequential)
product = ["visionary", "forge", "artisan"]

# Maintenance Track (Parallel to Product)
maintenance = ["janitor", "deps", "shepherd"]

# Quality Track (Parallel to Product)
quality = ["curator", "sentinel", "scribe"]
```

### 3.2 Task Management Integration
The file-based `.team/tasks/` system acts as a Kanban board.
**Issue:** It is disconnected from GitHub Issues.
**Recommendation:** Add a `TaskSyncer` component that:
1.  Parses `todo/*.md` files.
2.  Creates/Updates GitHub Issues with labels.
3.  Moves file to `done/` when Issue is closed (and vice versa).

---

## 4. Proposed Roadmap

### Phase 1: Technical Cleanup (Immediate)
- [ ] **Extract `SprintManager`**: Move from `legacy.py` to `repo/sprints.py`.
- [ ] **Extract Templates**: Move string constants to `repo/resources/templates.py` or `.team/templates/*.j2`.
- [ ] **Standardize Git**: Encapsulate all git operations in `BranchManager` (remove ad-hoc subprocess calls).
- [ ] **Harden Client**: Replace manual retries in `client.py` with `tenacity`.

### Phase 2: The Parallel Scheduler
- [ ] **Update Config**: Support `[tracks]` in `schedules.toml`.
- [ ] **Update V2**: Modify `execute_cycle_tick` to support multiple concurrent pointers (one per track).
- [ ] **Conflict Handling**: Enhance `ReconciliationManager` to handle merge conflicts between tracks.

### Phase 3: Intelligence Upgrade
- [ ] **Dynamic Scheduling**: Agents should request to run based on observation, not just cron.
- [ ] **Self-Healing**: If an agent fails repeatedly, the scheduler should quarantine it and notify the team.

---

## 5. Immediate Action Items

To start this process, I recommend the following refactoring steps for the next PR:

1.  **Isolate `SprintManager`**: It is a distinct domain and shouldn't be in the legacy scheduler.
2.  **Isolate `Templates`**: Clean up the python files by moving long strings out.
3.  **Update `client.py`**: Add `tenacity` retry logic.

These changes will shrink `scheduler_legacy.py` significantly, making the final V2 transition easier.
