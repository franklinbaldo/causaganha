Feature: Confidence Breakdown in Parquet (P2 - Medium Priority)
  As a quality engineer
  I want detailed confidence scores for each analysis component
  So that I can identify weak points and target improvements

  Background:
    Given the analysis system tracks confidence per component
    And components include: winner_id, loser_id, outcome, decision_type, judge_extraction

  @p2 @confidence @export
  Scenario: Export parquet with confidence breakdown
    Given I have 1000 analyzed decisions
    And each analysis includes component-level confidence scores
    When I export to parquet with schema v2
    Then the parquet file should contain "confidence_breakdown" struct column
    And the struct should include: overall, winner_identification, loser_identification, outcome_classification, decision_type_classification, judge_extraction
    And all confidence values should be between 0.0 and 1.0
    And the file size should increase by less than 1%

  @p2 @confidence @rag-breakdown
  Scenario: RAG analysis populates confidence breakdown
    Given I have a RAG analyzer configured
    When I analyze 100 decisions using RAG
    Then each result should have a confidence_breakdown
    And winner_identification confidence should be > 0.90 (RAG is good at this)
    And loser_identification confidence should be > 0.85
    And outcome_classification confidence should match rag_confidence
    And decision_type_classification should be ~0.50 (RAG struggles here)
    And judge_extraction should be ~0.30 (RAG can't extract judges well)

  @p2 @confidence @llm-breakdown
  Scenario: LLM analysis populates confidence breakdown
    Given I have an LLM analyzer configured
    When I analyze 50 decisions using LLM
    Then each result should have a confidence_breakdown
    And all component confidences should be > 0.70 (LLM is balanced)
    And winner_identification confidence should be ~0.92
    And judge_extraction confidence should be ~0.75 (better than RAG)
    And overall confidence should be the average of all components

  @p2 @confidence @targeted-reanalysis
  Scenario: Reanalyze only decisions with low component confidence
    Given I have a parquet file with 5000 decisions
    And 500 decisions have judge_extraction confidence < 0.60
    When I filter for confidence_breakdown.judge_extraction < 0.60
    And I reanalyze only these 500 decisions with improved judge extraction
    Then I should reanalyze only 10% of decisions (not all 5000)
    And the reanalysis should be targeted and cost-effective

  @p2 @confidence @quality-diagnostics
  Scenario: Identify weakest analysis components across dataset
    Given I have a parquet file with 10000 decisions
    When I calculate average confidence per component
    Then I should see a quality report like:
      | component                        | avg_confidence |
      | winner_identification            | 0.94           |
      | loser_identification             | 0.89           |
      | outcome_classification           | 0.83           |
      | decision_type_classification     | 0.58           |
      | judge_extraction                 | 0.42           |
    And I can prioritize improving "judge_extraction" (lowest score)

  @p2 @confidence @ab-testing
  Scenario: Compare model versions using confidence breakdown
    Given I have parquet files from two model versions
    When I compare average confidence breakdown between versions
    Then I can see which model improved on specific components
    And I can quantify the improvement per component

    Examples:
      | component              | model_v1 | model_v2 | improvement |
      | winner_identification  | 0.82     | 0.91     | +11%        |
      | judge_extraction       | 0.40     | 0.65     | +63%        |
      | outcome_classification | 0.80     | 0.83     | +4%         |

  @p2 @confidence @filter-high-quality
  Scenario: Filter for high-quality analyses across all components
    Given I have a parquet file with mixed confidence levels
    When I filter for decisions where all component confidences > 0.80
    Then I should get only high-quality analyses
    And I can use these as ground truth for training
    And I can study what makes these analyses confident

  @p2 @confidence @correlation-analysis
  Scenario: Analyze correlation between confidence and accuracy
    Given I have a parquet file with ground truth labels
    And decisions have confidence breakdown
    When I calculate accuracy by confidence level per component
    Then high confidence (>0.90) should correlate with high accuracy (>95%)
    And low confidence (<0.60) should correlate with lower accuracy (<80%)
    And I can calibrate confidence thresholds appropriately

  @p2 @confidence @hybrid-decision-tracking
  Scenario: Track which decisions used RAG vs LLM via confidence
    Given I have a parquet file from hybrid analysis
    When I analyze the analysis_method and confidence_breakdown fields
    Then decisions with analysis_method="rag" should have unbalanced confidences
    And decisions with analysis_method="hybrid" should show RAG confidence + LLM fallback
    And I can calculate the percentage that needed LLM fallback

  @p2 @confidence @component-specific-thresholds
  Scenario: Apply different confidence thresholds per component
    Given I have a parquet file with confidence breakdown
    And I set component-specific thresholds:
      | component              | threshold |
      | winner_identification  | 0.85      |
      | outcome_classification | 0.80      |
      | judge_extraction       | 0.50      |
    When I filter decisions that fail any threshold
    Then I can identify which specific aspects need reanalysis
    And I avoid reanalyzing decisions that are only weak in one component

  @p2 @confidence @training-data-curation
  Scenario: Select training data based on confidence breakdown
    Given I have 100000 decisions in parquet files
    When I select decisions where:
      | condition                                     |
      | winner_identification > 0.95                  |
      | AND loser_identification > 0.95               |
      | AND outcome_classification > 0.90             |
    Then I get high-quality training data for outcome classification
    And I can train RAG models with confident examples
    And I avoid noisy labels from uncertain analyses

  @p2 @confidence @backward-compatibility
  Scenario: Schema v1 files with only overall confidence still work
    Given I have a schema v1 parquet file with only confidence_score
    When I analyze decisions from the v1 file
    Then the system should treat confidence_score as overall confidence
    And the system should gracefully handle missing breakdown
    And queries should work with both v1 and v2 schemas

  @p2 @confidence @realtime-monitoring
  Scenario: Monitor confidence trends over time
    Given I have parquet files for the last 30 days
    When I calculate average confidence breakdown per day
    Then I can plot confidence trends over time
    And I can detect if a component's confidence is degrading
    And I can alert when average confidence drops below thresholds
