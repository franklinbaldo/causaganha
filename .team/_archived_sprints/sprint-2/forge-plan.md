# Plan: Forge - Sprint 2

**Persona:** Forge ⚒️
**Sprint:** 2
**Created:** 2026-01-26 (Updated)
**Priority:** High

## Objectives
My mission is to complete the "Portal" visual identity and ensure a polished user experience.

<<<<<<< HEAD
- [ ] **Consolidate CSS Architecture:** Address CSS shadowing issues by merging `.about-container` styles from `docs/stylesheets/extra.css` into `overrides/stylesheets/extra.css` and unifying `.post-card-modern` with `.md-post--card` glassmorphism.
- [ ] **Functional Social Cards:** Ensure `og:image` tags are generated correctly and do not return 404s. (Requires `pillow`, `cairosvg`).
- [ ] **Custom Favicon:** Implement a unique favicon for the site.
- [ ] **Refine "Empty State":** Polish the "Welcome" message on the homepage to be engaging even without content.
- [ ] **Accessibility Audit (Preliminary):** Run a basic accessibility check (Lighthouse/Axe) on the new "Portal" theme to catch low-hanging fruit (contrast, labels).

## Dependencies
- **Curator:** For approval of visual refinements.

## Context
Foundational theming was established in Sprint 1. Sprint 2 is about "Finish and Polish".

## Expected Deliverables
1. Consolidated CSS file (`overrides/stylesheets/extra.css`) with no shadowing.
2. Working Social Cards.
3. Custom Favicon.
4. Polished Empty State.
5. Accessibility Report.
=======
**Created:** 2026-01-24
**Priority:** High

## Objectives
My mission is to transform the UX vision into high-performance web components. For Sprint 2, I will focus on executing the visual identity and structural fixes defined by the Curator.

- [ ] **Implement Custom Visual Identity:** Apply the new color palette and favicon across all templates, replacing the default Material theme look.
- [ ] **Fix Frontend Broken Links/Assets:** Resolve the missing CSS file issues and ensure social card images are generated and linked correctly (fixing 404s).
- [ ] **Enhance Empty State:** Redesign the "empty state" homepage to be more welcoming and informative for new users.
- [ ] **Verify Mobile Responsiveness:** Ensure all changes look good and function correctly on mobile viewports.

## Dependencies
- **Curator:** I am dependent on the Curator to provide the specific design specifications (colors, assets, copy) via tasks in `.team/tasks/`.

## Context
In Sprint 1, we identified that the generated blogs look too generic and have some broken visual elements. Sprint 2 is about "polishing the surface" to ensure that the out-of-the-box experience for an Egregora user is professional and distinct.

## Expected Deliverables
1. **Updated Templates:** `src/egregora/rendering/templates/` will be updated with new CSS and HTML overrides.
2. **Fixed Scaffolding:** The site generation logic will correctly place favicons and assets.
3. **Visual Verification:** Screenshots demonstrating the new look and the absence of 404 errors in the console.
>>>>>>> origin/pr/2732

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Social Card generation fails in CI | Medium | Medium | I will ensure the necessary dependencies (CairoSVG, Pillow) are correctly handled in the environment or the generation logic degrades gracefully. |
| Custom CSS conflicts with Material updates | Low | Low | I will keep overrides minimal and scoped, as learned in Sprint 1. |

## Proposed Collaborations
- **With Curator:** Regular syncs (via tasks) to review visual changes.
