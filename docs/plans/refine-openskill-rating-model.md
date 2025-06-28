# Refine OpenSkill Rating Model

## Problem Statement
- **What problem does this solve?**
  The current OpenSkill rating implementation in CausaGanha provides a valuable measure of lawyer performance. However, it's based on a relatively simple model of wins, losses, and draws. It doesn't account for factors like the complexity of a case, the significance of the decision, or the freshness of a lawyer's activity, which could lead to a more nuanced and accurate assessment of skill.
- **Why is this important?**
  Refining the rating model can lead to more accurate, fair, and insightful lawyer skill assessments. This increases the credibility and utility of the CausaGanha platform. For example, winning a highly complex case against a strong opponent should arguably have a greater positive impact on a rating than winning a simple case.
- **Current limitations**
  - The model primarily uses binary outcomes (win/loss/draw for Team A vs. Team B).
  - It does not explicitly factor in case complexity, monetary value involved, or type of legal matter.
  - Ratings do not currently decay over time for inactive lawyers, potentially keeping ratings stale.
  - "Partial wins" (parcialmente procedente) are treated as full wins for the plaintiff, which might not always be accurate.

## Proposed Solution
- **High-level approach**
  Explore and implement enhancements to the OpenSkill rating model by incorporating additional factors. This will involve research into OpenSkill library capabilities, potential modifications to how match outcomes are determined or weighted, and changes to the data fed into the rating updates.
- **Technical architecture Ideas (to be explored and chosen from)**
  1.  **Weighted Matches based on Case Complexity/Significance**:
      - **Concept**: Assign a weight to each match based on objective factors (e.g., monetary value, type of procedure, court level if multi-tribunal data is available). More significant matches could have a larger impact on rating changes.
      - **Implementation**:
          - Requires extracting complexity/significance factors during LLM processing.
          - The OpenSkill library's `tau` parameter (dynamics factor) or adjusting `beta` on a per-match basis could be explored, or a custom scaling of rating changes post-calculation.
          - Modify the `partidas` table or input to `rate_teams` to include this weight.
  2.  **Time Decay for Ratings**:
      - **Concept**: Gradually increase the `sigma` (uncertainty) of lawyers who have not participated in matches for a certain period, or slightly decrease `mu` over time.
      - **Implementation**:
          - OpenSkill's `rate` function has a `decay` argument. This could be applied periodically (e.g., via a scheduled job or CLI command).
          - Requires tracking the last activity date for each lawyer.
  3.  **More Nuanced Outcome Handling**:
      - **Concept**: Refine how "parcialmente procedente" (partially upheld) and other non-binary outcomes are translated into OpenSkill ranks or scores.
      - **Implementation**:
          - The `MatchResult.PARTIAL_A` / `PARTIAL_B` enum values from `pipeline.py` (if still relevant) and associated `tau` adjustments in `openskill_rating.py` were a step in this direction. This needs to be properly integrated if LLM can reliably extract such nuances.
          - Could involve mapping certain outcomes to a draw with a slight bias, or using different `tau` values.
  4.  **Activity Threshold for Ranking Display**:
      - **Concept**: Only display lawyers in rankings if they have a minimum number of recent matches to ensure ratings are current and based on sufficient activity.
      - **Implementation**: Filter the output of `causaganha stats` or dashboard views based on `total_partidas` and potentially `updated_at` from the `ratings` table.
  5.  **Separate Ratings for Different Legal Areas (Future)**:
      - **Concept**: If data allows for classification of cases by legal area (e.g., civil, criminal, labor), maintain separate OpenSkill ratings for lawyers in each area.
      - **Implementation**: This is a major extension, requiring significant changes to data models and processing.

- **Implementation steps (Focusing on 1-2 initial refinements)**
  *Assume focusing on "Time Decay" and "More Nuanced Outcome Handling" initially.*
  1.  **Phase 1: Research and Design (Week 1)**
      - Research OpenSkill library's capabilities for time decay (`decay` parameter in `rate` function) and handling partial outcomes (e.g., impact of `tau`).
      - Design how to integrate time decay: a periodic script, or on-the-fly adjustment during rating retrieval if a lawyer has been inactive.
      - Define a clearer mapping from LLM-extracted decision results (e.g., "parcialmente procedente," "extinto sem resolução de mérito") to OpenSkill inputs (ranks, scores, or `tau` adjustments).
  2.  **Phase 2: Implement Time Decay (Weeks 2-3)**
      - Add a `last_activity_at` timestamp to the `ratings` table, updated whenever a lawyer participates in a match.
      - Create a new CLI command (e.g., `causaganha ratings decay [--threshold_days N]`) that iterates through lawyers, checks `last_activity_at`, and applies rating decay using OpenSkill's `decay` functionality if applicable.
      - Test the decay mechanism thoroughly.
  3.  **Phase 3: Implement Nuanced Outcome Handling (Weeks 4-5)**
      - Enhance LLM prompt/parsing to more reliably extract nuanced outcomes if necessary.
      - Modify `_update_ratings_logic` (or its equivalent in the new CLI structure) in `src/pipeline.py` or `src/cli.py` (score command).
      - When processing a decision, map the nuanced outcome to appropriate OpenSkill parameters (e.g., adjust `tau` for the match, or use fractional scores if OpenSkill supports it directly, or treat as a draw with conditions).
      - Test how different mappings affect rating stability and perceived fairness.
  4.  **Phase 4: Testing, Analysis, and Documentation (Week 6)**
      - Analyze the impact of these changes on the overall rating distribution and individual lawyer ratings.
      - Compare new ratings with old ratings for a sample set to understand the effect.
      - Document the new rating model refinements, including how decay and nuanced outcomes are handled.

## Success Criteria
- **Improved Rating Nuance**: The rating system reflects more factors than just simple win/loss, leading to potentially more accurate skill assessments.
- **Time Decay Implemented**: Ratings for inactive lawyers show increased uncertainty or slight decay over time.
- **Nuanced Outcomes Handled**: "Parcialmente procedente" and similar outcomes are handled more effectively than treating them as simple wins/losses.
- **Model Stability**: The refined model remains stable and does not produce erratic rating swings without cause.
- **Understandability**: The logic behind rating adjustments remains understandable and can be explained.
- **Configurability (Optional)**: Parameters for decay or outcome weighting are configurable if appropriate.

## Implementation Plan (High-Level for this document - Time Decay & Nuanced Outcomes)
1.  **Research OpenSkill Decay/Tau**: Understand library features. Design decay application logic and outcome mapping.
2.  **Implement Time Decay**: Add `last_activity_at` to `ratings`. Create `causaganha ratings decay` command. Test.
3.  **Implement Nuanced Outcomes**: Enhance LLM if needed. Modify rating update logic to use nuanced outcome mapping (e.g., via `tau` or adjusted ranks). Test.
4.  **Analyze & Document**: Study impact on ratings. Document the refined model.

## Risks & Mitigations
- **Risk 1: Model Complexity**: Adding too many factors can make the rating model overly complex, hard to understand, and difficult to tune.
  - *Mitigation*: Introduce refinements one at a time. Start with simpler adjustments. Clearly document the impact of each new factor.
- **Risk 2: Subjectivity**: Factors like "case complexity" can be subjective and hard to quantify objectively from text.
  - *Mitigation*: Focus initially on more objective factors if possible (e.g., time decay, clearer outcome mapping). If complexity is pursued, use clearly defined, measurable proxies extracted by the LLM and acknowledge their limitations.
- **Risk 3: Data Requirements**: Some refinements (like case complexity) require richer data from the LLM extraction stage.
  - *Mitigation*: Coordinate with efforts to improve LLM prompts and extraction. If data is unavailable, defer the specific refinement.
- **Risk 4: Unintended Consequences**: Changes to the rating model can have unexpected impacts on the rankings.
  - *Mitigation*:
    - Thoroughly test changes on a snapshot of existing data and compare with previous rating calculations.
    - Simulate changes and analyze their effect before deploying them.
    - Consider A/B testing different model parameters if feasible.
- **Risk 5: OpenSkill Library Limitations**: The OpenSkill library might not directly support all desired refinements.
  - *Mitigation*: Explore creative uses of existing parameters (`tau`, `beta`, `decay`). If direct support is lacking, consider custom adjustments to inputs or outputs of the OpenSkill functions, while still using its core rating update mechanism.

## Dependencies
- The quality of LLM extraction (for nuanced outcomes or case complexity factors).
- The existing OpenSkill integration in `src/openskill_rating.py` and `src/pipeline.py` (or `src/cli.py score` command).
- Database schema (potential additions like `last_activity_at` or complexity scores).
- `openskill` Python library.
