# Plan: Curator 🎭 - Sprint 3

**Persona:** Curator
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
With the visual identity established in Sprint 2, Sprint 3 shifts focus to the core "Reading Experience" and "Content Discovery".

<<<<<<< HEAD
- [ ] **Reading Experience Polish:** Deep dive into typography (line-height, measure, font-weight) and mobile responsiveness. Ensure long-form content is comfortable to read on any device.
- [ ] **Content Discovery UI:** Design and specify the UI for "Related Content" and the "Code References" feature (collaborating with Visionary).
- [ ] **100% Lighthouse Accessibility:** Aim for a perfect accessibility score. Move from "audit" to "fix".
- [ ] **Search Experience:** Evaluate and refine the search UI (standard MkDocs vs specialized implementation).

## Dependencies
- **Forge:** To implement the CSS tweaks for reading experience.
- **Visionary:** To provide the backend data for "Code References" so we can style them.

## Context
A pretty blog is useless if it's hard to read or if users can't find relevant content. Sprint 3 is about utility and depth.

## Expected Deliverables
1. **Typography Style Guide:** A section in `docs/ux-vision.md` defining the exact typographic scale and rules.
2. **"Code Reference" UI Spec:** A clear design for how code links should appear.
3. **Lighthouse Score Report:** Showing 100 (or near 100) on Accessibility.
=======
My mission is to design the user experience for the new "Context Layer" (Git History and Code References) and ensure the site evolves into a true "Symbiote" interface.

- [ ] **Context Layer UX:** Design how Git history and code references are presented to the user. How does a user "travel back in time" via a link?
- [ ] **Structured Sidecar UI:** Ensure that the structured data exposed by the backend is presented meaningfully in the UI (e.g., rich metadata sidebars, improved search facets).
- [ ] **Mobile Refinement:** Perform a dedicated mobile UX audit and refinement pass, ensuring the "Portal" experience works on small screens.

## Dependencies
- **Visionary & Simplifier:** Definition of the "Context Layer" capabilities.
- **Forge:** Implementation of the new UI components.

## Context
Sprint 3 moves beyond static polish into dynamic interaction. The "Symbiote Shift" adds a temporal dimension (history) to the content. This presents significant UX challenges: how to show this complexity without overwhelming the user?

## Expected Deliverables
1. **Context Layer Mockups/Specs:** detailed specifications for how history links should look and behave.
2. **Mobile UX Report:** specific tasks for mobile optimization.
>>>>>>> origin/pr/2881

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
<<<<<<< HEAD
| Mobile layout is neglected | Medium | High | I will perform all my validations primarily on mobile viewports. |
| "Code References" are noisy | Medium | Medium | We will design them to be unobtrusive (e.g., sidenotes or tooltips) rather than interrupting the flow. |

## Proposed Collaborations
- **With Visionary:** To finalize the "Code Reference" UI.
- **With Forge:** To implement the detailed typographic refinements.
=======
| Context Layer is too complex for users | High | High | I will advocate for "progressive disclosure" – hiding complexity until requested. |
| Mobile experience is neglected | Medium | Medium | I have dedicated a specific objective to Mobile Refinement. |

## Proposed Collaborations
- **With Visionary:** To understand the full scope of the "Context Layer".
- **With Forge:** To prototype the new UI components.
>>>>>>> origin/pr/2881
