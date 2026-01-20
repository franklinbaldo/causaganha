Feature: Data Quality and Validation
  As a data analyst
  I want to ensure extracted data is accurate and valid
  So that lawyer ratings and analyses are trustworthy

  Background:
    Given the CausaGanha database is initialized
    And data quality checks are enabled

  # ============================================================================
  # INTIMATION DATA QUALITY
  # ============================================================================

  Scenario: Validate case number format
    Given an intimation with case number "0001234-56.2024.8.22.0001"
    When the case number is validated
    Then the format should match the CNJ standard pattern
    And the validation should pass

  Scenario: Reject malformed case numbers
    Given an intimation with case number "123-invalid"
    When the case number is validated
    Then the validation should fail
    And an error should be logged about invalid format
    And the intimation should be flagged for review

  Scenario: Validate tribunal codes against known list
    Given an intimation with tribunal code "TJRO"
    When the tribunal code is validated
    Then the code should be in the list of valid tribunals
    And the validation should pass

  Scenario: Reject unknown tribunal codes
    Given an intimation with tribunal code "TJXX"
    When the tribunal code is validated
    Then the validation should fail
    And an error should be logged about unknown tribunal
    And the intimation should be rejected

  Scenario: Validate PDF URLs are accessible
    Given an intimation with PDF URL "https://pje.tjro.jus.br/docs/decision.pdf"
    When the URL is validated
    Then the URL should have valid format
    And the URL should be accessible (returns 200 OK)
    And the validation should pass

  Scenario: Detect duplicate intimations by hash
    Given an intimation with hash "abc123def456"
    And the same hash already exists in the database
    When the intimation is validated
    Then a duplicate should be detected
    And the intimation should be skipped
    And a warning should be logged

  # ============================================================================
  # LAWYER DATA QUALITY
  # ============================================================================

  Scenario: Validate OAB number format
    Given a lawyer with OAB "123456"
    When the OAB number is validated
    Then the format should be numeric
    And the length should be between 4 and 7 digits
    And the validation should pass

  Scenario: Validate Brazilian state codes
    Given a lawyer with state "SP"
    When the state code is validated
    Then the code should be in the list of valid Brazilian states
    And the validation should pass

  Scenario: Reject invalid state codes
    Given a lawyer with state "XX"
    When the state code is validated
    Then the validation should fail
    And an error should be logged
    And the lawyer association should be flagged

  Scenario: Normalize OAB numbers consistently
    Given raw OAB numbers in different formats:
      | Input         | Expected  |
      | 123456        | 123456    |
      | OAB/SP 123456 | 123456    |
      | 123.456       | 123456    |
    When the OAB numbers are normalized
    Then all should result in the expected format
    And states should be extracted separately

  Scenario: Detect and flag duplicate lawyer entries
    Given lawyer "123456/SP" appears multiple times in an intimation
    When lawyer associations are validated
    Then the duplicate should be detected
    And only one entry should be stored
    And a warning should be logged

  # ============================================================================
  # ANALYSIS DATA QUALITY
  # ============================================================================

  Scenario: Validate decision types against allowed values
    Given an analysis with decision type "SENTENÇA"
    When the decision type is validated
    Then the type should be in the allowed list
    And the validation should pass

  Scenario: Reject invalid decision types
    Given an analysis with decision type "INVALID_TYPE"
    When the decision type is validated
    Then the validation should fail
    And the analysis should be rejected
    And an error should be logged

  Scenario: Validate outcome values
    Given an analysis with outcome "PROCEDENTE"
    When the outcome is validated
    Then the outcome should be in the allowed list
    And the validation should pass

  Scenario: Validate confidence scores are in valid range
    Given an analysis with confidence score 0.85
    When the confidence is validated
    Then the score should be between 0.0 and 1.0
    And the validation should pass

  Scenario: Reject invalid confidence scores
    Given an analysis with confidence score 1.5
    When the confidence is validated
    Then the validation should fail
    And the analysis should be rejected
    And an error should be logged

  Scenario: Validate winner and loser are different
    Given an analysis where winner is "123456/SP"
    And loser is also "123456/SP"
    When the analysis is validated
    Then the validation should fail
    And an error should be logged about same winner/loser
    And the analysis should be rejected

  Scenario: Validate required fields are present
    Given an analysis missing the "outcome" field
    When the analysis is validated
    Then the validation should fail
    And the missing field should be identified
    And the analysis should be rejected

  # ============================================================================
  # CROSS-FIELD VALIDATION
  # ============================================================================

  Scenario: Verify winner matches outcome logic
    Given an analysis with outcome "PROCEDENTE"
    And the winner is the defendant's lawyer
    When cross-field validation is performed
    Then a warning should be raised
    And the analysis should be flagged for review
    And the inconsistency should be logged

  Scenario: Verify lawyer OAB matches state in analysis
    Given an intimation has lawyer "123456/SP" (São Paulo)
    And the analysis identifies winner as "123456/RJ" (Rio de Janeiro)
    When cross-field validation is performed
    Then the state mismatch should be detected
    And a warning should be logged
    And the analysis should be flagged for review

  # ============================================================================
  # RATING DATA QUALITY
  # ============================================================================

  Scenario: Validate rating values are reasonable
    Given a lawyer rating with mu=35.0 and sigma=4.5
    When the rating is validated
    Then mu should be positive
    And sigma should be positive
    And the conservative estimate should be calculated correctly
    And the validation should pass

  Scenario: Detect anomalous rating changes
    Given lawyer "123456/SP" has rating mu=30.0
    And after one match, the new mu is 50.0 (20 point jump)
    When the rating change is validated
    Then the anomalous change should be detected
    And a warning should be logged
    And the rating update should be flagged for review

  Scenario: Validate win/loss statistics consistency
    Given a lawyer has wins=15 and losses=5
    And total_matches=18
    When the statistics are validated
    Then the inconsistency should be detected (15+5=20, not 18)
    And the error should be logged
    And the statistics should be corrected

  # ============================================================================
  # COMPLETENESS CHECKS
  # ============================================================================

  Scenario: Check completeness of pipeline stages
    Given 100 intimations were collected
    When I check pipeline completeness
    Then I should verify how many were archived
    And I should verify how many were analyzed
    And I should verify how many were scored
    And completeness percentages should be calculated

  Scenario: Identify stuck intimations
    Given intimations collected over 7 days ago
    And they are still unarchived
    When I run the completeness check
    Then stuck intimations should be identified
    And a report should list the stuck items
    And reasons for stuck state should be investigated

  Scenario: Track data freshness
    Given the last collection was 48 hours ago
    When I check data freshness
    Then a warning should be raised about stale data
    And the timestamp of last collection should be shown
    And a suggestion to run collection should be provided

  # ============================================================================
  # CONSISTENCY CHECKS
  # ============================================================================

  Scenario: Verify referential integrity
    Given an analysis references intimation "int-123"
    And intimation "int-123" does not exist in the database
    When referential integrity is checked
    Then the orphaned analysis should be detected
    And an error should be logged
    And the analysis should be marked as invalid

  Scenario: Verify lawyer rating references valid analyses
    Given a lawyer rating update references analysis "ana-456"
    And analysis "ana-456" is marked as invalid
    When consistency is checked
    Then the inconsistency should be detected
    And the rating update should be questioned
    And a review should be triggered

  Scenario: Check for orphaned records
    Given the database contains analysis records
    When I run the orphan check
    Then any analyses without corresponding intimations should be found
    And any ratings without corresponding analyses should be found
    And a cleanup recommendation should be provided

  # ============================================================================
  # ACCURACY VERIFICATION
  # ============================================================================

  Scenario: Sample and manually verify LLM analyses
    Given 1000 analyses have been performed
    When I run accuracy verification
    Then a random sample of 50 analyses should be selected
    And the sample should be flagged for manual review
    And reviewers should compare LLM output to actual PDFs
    And accuracy metrics should be calculated

  Scenario: Compare ML predictions to LLM analyses
    Given both ML and LLM analyses are enabled
    And 500 decisions have been analyzed
    When I check prediction accuracy
    Then ML predictions should be compared to LLM results
    And agreement rate should be calculated
    And significant disagreements should be identified
    And disagreements should be reviewed

  Scenario: Validate winner identification accuracy
    Given a sample of 100 analyses
    When I manually review winner identification
    Then correct identifications should be counted
    And errors should be categorized (wrong OAB, wrong state, wrong winner)
    And accuracy percentage should be calculated
    And error patterns should be identified

  # ============================================================================
  # DATA QUALITY METRICS
  # ============================================================================

  Scenario: Calculate data quality score
    When I run the data quality report
    Then completeness score should be calculated (% of completed pipeline stages)
    And validity score should be calculated (% passing validation)
    And accuracy score should be calculated (% of verified correct analyses)
    And an overall data quality score should be computed
    And the score should be tracked over time

  Scenario: Track quality trends over time
    Given data quality metrics are collected daily
    When I view the quality dashboard
    Then quality scores should be plotted over time
    And trends should be identified (improving/degrading)
    And anomalies should be highlighted
    And alerts should be raised for degrading quality

  # ============================================================================
  # AUTOMATED QUALITY CHECKS
  # ============================================================================

  Scenario: Run automated quality checks on new data
    Given new intimations are collected
    When the quality check runs automatically
    Then case number format should be validated
    And tribunal codes should be validated
    And PDF URLs should be validated
    And duplicate detection should run
    And a quality report should be generated

  Scenario: Block pipeline on low quality data
    Given automated quality checks are enabled
    And the quality score falls below 70%
    When I attempt to run the pipeline
    Then the pipeline should be blocked
    And a warning should be displayed about low quality
    And the quality issues should be listed
    And remediation should be required before proceeding

  # ============================================================================
  # CONFIDENCE LEVEL TRACKING
  # ============================================================================

  Scenario: Track confidence distribution over time
    Given 1000 analyses have been performed
    When I check confidence distribution
    Then analyses should be grouped by confidence ranges:
      | Range     | Count |
      | 0.0-0.3   | 50    |
      | 0.3-0.6   | 150   |
      | 0.6-0.8   | 400   |
      | 0.8-1.0   | 400   |
    And low confidence analyses should be flagged
    And high confidence rate should be tracked

  Scenario: Alert on decreasing confidence trends
    Given average confidence was 0.85 last week
    And average confidence is 0.65 this week
    When the trend is analyzed
    Then a warning should be raised about degrading confidence
    And potential causes should be investigated
    And the LLM model performance should be reviewed

  # ============================================================================
  # DATA SANITIZATION
  # ============================================================================

  Scenario: Sanitize text fields for special characters
    Given a lawyer name contains special characters "João D'Silva"
    When the name is sanitized
    Then special characters should be handled correctly
    And the name should be stored without corruption
    And retrieval should return the correct name

  Scenario: Normalize whitespace in text fields
    Given a decision reasoning with irregular whitespace "  Multiple   spaces  "
    When the text is normalized
    Then excessive whitespace should be reduced
    And the text should be "Multiple spaces"
    And formatting should be consistent

  # ============================================================================
  # AUDIT TRAIL
  # ============================================================================

  Scenario: Maintain audit trail for data changes
    Given a lawyer rating is updated
    When the update is committed
    Then the previous rating should be recorded in audit log
    And the new rating should be recorded
    And the timestamp should be recorded
    And the reason for change should be recorded

  Scenario: Track data quality issues in audit log
    Given a validation error occurs
    When the error is handled
    Then the error should be recorded in audit log
    And the affected record should be identified
    And the validation rule violated should be recorded
    And the timestamp should be recorded

  # ============================================================================
  # QUALITY REPORTING
  # ============================================================================

  Scenario: Generate comprehensive data quality report
    When I request a data quality report
    Then the report should include validation statistics
    And the report should include completeness metrics
    And the report should include accuracy samples
    And the report should include confidence distributions
    And the report should include identified issues
    And the report should include recommendations

  Scenario: Export data quality metrics for external analysis
    When I export quality metrics
    Then the export should be in CSV format
    And the export should include all quality dimensions
    And the export should include timestamps
    And the export should be importable to BI tools
