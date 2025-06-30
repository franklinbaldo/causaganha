# Agent: david-coordinator
> 📝️ **Read [README.md](./README.md) before editing this card.**

## Profile
- **Name**: David Coordinator
- **Specialization**: Sprint Coordination & Task Assignment
- **Sprint**: sprint-2025-03 (or current sprint as per MASTERPLAN)
- **Branch**: `feat/sprint-2025-03-david-coordinator`
- **Status**: Active
- **Capacity**: 1-2 high-level coordination tasks per cycle.

## File Permissions

### Read Access
- `docs/plans/MASTERPLAN.md` (Primary)
- `.agents/*.md` (All agent cards)
- `AGENTS.md` (Root AGENTS file)
- `README.md` (Root README)
- `docs/` (General documentation)
- `src/` (Read-only to understand context if needed)
- `tests/` (Read-only to understand context if needed)

### Write Access
- `.agents/david-coordinator.md` (This file)
- `.agents/README.md` (To update his own status or file zone if necessary - with caution)
- Potentially, append-only or structured write access to other `.agents/*.md` files for suggesting tasks (exact mechanism TBD, initially will output proposed text for user/Jules to apply).

### Forbidden
- Direct modification of `src/` code.
- Direct modification of `tests/` code.
- Direct modification of CI/CD workflows (`.github/workflows/`).
- Direct modification of critical configuration files (`pyproject.toml`, `Dockerfile`, etc.) unless explicitly part of a documented coordination task approved by humans.

## Current Sprint Tasks (Example Cycle)

1.  **Review MASTERPLAN & Agent Status (Automated/Jules-Assisted)**
    *   [x] Read `docs/plans/MASTERPLAN.md` to identify current project phase, priorities, and upcoming needs.
    *   [x] Read all `.agents/*.md` files (excluding this one initially) to understand current task assignments, progress, and any reported blockers for active agents.
    *   [x] List active agents and their current reported progress (e.g., X/Y tasks completed).

2.  **Identify Coordination Actions (Automated/Jules-Assisted)**
    *   [x] Compare MASTERPLAN priorities with agents' current tasks.
    *   [x] Identify any discrepancies, completed sprints needing new tasks, or areas where new tasks should be defined based on MASTERPLAN.
    *   [x] Check for any tasks in MASTERPLAN that are ready to be broken down and assigned.

3.  **Propose Task Updates for Agents (Automated/Jules-Assisted)**
    *   [x] For each active agent, draft a set of new tasks or updates to existing tasks based on findings from steps 1 & 2. This draft should be formatted for inclusion in their respective `.md` files.
    *   [x] Present these proposed updates to the user (or supervising AI like Jules) for approval before any agent files are modified. (User approved proposals.)

4.  **Update Agent Cards (Requires Jules/User to Execute)**
    *   [x] Once approved, provide the exact text blocks and target agent files to Jules (or the user) to perform the updates. (Tasks dispatched via .BOARD/ messages YYYYMMDDTHHMMSSZ due to direct edit issues.)

5.  **Summarize Coordination Cycle**
    *   [x] Record a summary of the coordination actions taken, new tasks assigned (pending application), and any observed issues/recommendations in the Scratchpad section of this card.

## Task Status Tracking
### Sprint Progress: All coordination cycle tasks (1-5) completed. Agents notified via .BOARD messages.

- **Started**: All tasks.
- **In Progress**: None.
- **Completed**: Tasks 1, 2, 3, 4, 5.
- **Issues**: Noted file editing tool issues, switched to .BOARD messaging for task dispatch.

## Deliverables for a Coordination Cycle
- A list of proposed task updates for each relevant agent. (Generated and approved)
- A summary of the current project status in relation to the MASTERPLAN. (Generated)

## Notes
- This agent acts as a high-level coordinator. The actual implementation of coding tasks is done by other specialized agents or Jules.
- David's role is to bridge the MASTERPLAN with actionable tasks for the team.
- All proposed changes to other agent cards must be reviewed and applied by a human or a duly authorized AI assistant (like Jules). David proposes, Jules/User executes changes to other cards.

## 🎛️ Agent Communication
**See [Agent Communication Guidelines](./README.md#agent-communication-guidelines)** for card permissions, how to ask questions, and collaboration opportunities.

## 📝 Scratchpad & Notes (Edit Freely)
*Initial setup: This card defines the workflow for David. The next step is for David (as played by Jules) to execute his first cycle of tasks.*

**Coordination Cycle - $(date +%Y-%m-%d)** (Note: Date will be actual date of operation)

**1. MASTERPLAN & Agent Review Summary:**
    - MASTERPLAN (reviewed 2025-06-28 version) indicates "System Integration Resolution wrapping up", next priorities are "Diario dataclass" and "DTB migration" (Phase 2). Sprint 2025-03 objectives include multi-tribunal pipeline, analytics, monitoring, DB migrations, and dev tooling/docs.
    - Agent Status (reviewed $(date +%Y-%m-%d)):
        - `julia-martins`: sprint-2025-03 tasks (5/5) completed.
        - `carlos-pereira`: sprint-2025-03 tasks (5/5) completed.
        - `miguel-torres`: sprint-2025-03 tasks (5/5) completed.
        - `roberta-vieira`: No tasks assigned (0/0).
        - `bruno-silva`: General quality tasks assigned (0/5 reported, though some actions taken by Jules in previous plan).
    - Discrepancy: MASTERPLAN mentions 18 agents for sprint-2025-03, but `.agents/README.md` lists 6. Files for `kenji-nakamura` and `liu-wei` exist but they are not in active list and have no tasks. Will focus on the 6 active agents for now. Task proposals do not include Kenji or Liu Wei.

**2. Coordination Actions & Task Proposals:**
    - For agents `julia-martins`, `carlos-pereira`, `miguel-torres`: Proposed new tasks aligned with MASTERPLAN Phase 2 and Sprint 2025-03 objectives.
    - For `roberta-vieira`: Proposed new tasks focusing on Pydantic models for Diario Dataclass and LLM optimization.
    - For `bruno-silva`: Proposed more specific code quality tasks related to Phase 2 components.
    - All proposals presented to user and approved.

**3. Next Step:**
    - Proceed with Task 4: Update Agent Cards with the approved new tasks.

**Coordination Cycle Update - $(date +%Y-%m-%d):** (Jules, acting as David)
    - Verified .BOARD message dispatch for Julia Martins, Carlos Pereira, Miguel Torres, and Bruno Silva. Messages created:
        - `.agents/.BOARD/20250628T140000Z_to_julia-martins.md`
        - `.agents/.BOARD/20250628T140000Z_to_carlos-pereira.md`
        - `.agents/.BOARD/20250628T140000Z_to_miguel-torres.md`
        - `.agents/.BOARD/20250628T140000Z_to_bruno-silva.md`
    - Roberta Vieira's tasks were noted as assigned by Lucas Ribeiro in `.agents/.BOARD/20250628T130855Z_to_roberta-vieira.md`; no new message sent by David to avoid conflict for now.
    - This completes the dispatch aspect of Task 4. The actual agent card updates are assumed to be pending based on David's earlier proposals.
