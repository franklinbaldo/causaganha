Feature: AI-Powered Decision Analysis
  As a legal analyst
  I want decisions to be automatically analyzed by AI
  So that I can extract structured legal information at scale

  Background:
    Given the CausaGanha database is initialized
    And the Gemini LLM API is accessible
    And the decision analyzer is configured with model "gemini-2.0-flash-exp"

  # ============================================================================
  # CORE ANALYSIS SCENARIOS
  # ============================================================================

  Scenario: Analyze a simple sentença with clear winner
    Given an unanalyzed intimation with ID "intimacao-001"
    And the PDF contains a "SENTENÇA" with outcome "PROCEDENTE"
    And the plaintiff is represented by lawyer "123456/SP"
    And the defendant is represented by lawyer "234567/RJ"
    When I run the analyze command
    Then the decision_analysis table should contain 1 new record
    And the analysis should identify winner as "123456/SP"
    And the analysis should identify loser as "234567/RJ"
    And the decision type should be "SENTENÇA"
    And the outcome should be "PROCEDENTE"
    And the confidence score should be above 0.8

  Scenario: Analyze an acórdão (appellate decision)
    Given an unanalyzed intimation with a PDF containing an "ACÓRDÃO"
    And the decision text states "NEGADO PROVIMENTO AO RECURSO"
    And the appellant is represented by lawyer "345678/MG"
    And the appellee is represented by lawyer "456789/SP"
    When I run the analyze command
    Then the decision type should be "ACÓRDÃO"
    And the outcome should be "IMPROCEDENTE" for the appellant
    And the winner should be the appellee's lawyer "456789/SP"
    And the loser should be the appellant's lawyer "345678/MG"

  Scenario: Extract judge information from decision
    Given an unanalyzed intimation with PDF
    And the decision is signed by "Juiz Dr. Carlos Alberto Silva"
    When I run the analyze command
    Then the analysis should record judge name as "Carlos Alberto Silva"
    And the judge name should be normalized (title removed)

  Scenario: Extract reasoning from decision text
    Given an unanalyzed intimation with PDF
    And the decision includes reasoning "Ausência de provas suficientes para condenação"
    When I run the analyze command
    Then the analysis should capture the reasoning text
    And the reasoning should be a concise summary
    And the reasoning length should be between 10 and 500 characters

  # ============================================================================
  # DECISION TYPES & OUTCOMES
  # ============================================================================

  Scenario Outline: Identify different decision types correctly
    Given an unanalyzed intimation with PDF
    And the PDF contains decision type "<decision_type>"
    When I run the analyze command
    Then the decision type should be "<expected_type>"

    Examples:
      | decision_type               | expected_type              |
      | SENTENÇA                    | SENTENÇA                   |
      | ACÓRDÃO                     | ACÓRDÃO                    |
      | DECISÃO INTERLOCUTÓRIA      | DECISÃO INTERLOCUTÓRIA     |
      | Sentença (lowercase)        | SENTENÇA                   |

  Scenario Outline: Classify decision outcomes accurately
    Given an unanalyzed intimation with PDF
    And the decision states "<outcome_text>"
    When I run the analyze command
    Then the outcome should be "<expected_outcome>"

    Examples:
      | outcome_text                          | expected_outcome              |
      | JULGO PROCEDENTE O PEDIDO             | PROCEDENTE                    |
      | JULGO IMPROCEDENTE A AÇÃO             | IMPROCEDENTE                  |
      | JULGO PARCIALMENTE PROCEDENTE         | PARCIALMENTE PROCEDENTE       |
      | EXTINGO O PROCESSO SEM MÉRITO         | EXTINTO SEM RESOLUÇÃO MÉRITO  |
      | DECLARO A PRESCRIÇÃO                  | EXTINTO SEM RESOLUÇÃO MÉRITO  |

  # ============================================================================
  # LAWYER IDENTIFICATION
  # ============================================================================

  Scenario: Identify winner and loser from procedente sentença
    Given an unanalyzed intimation with PDF
    And the decision is "SENTENÇA" with outcome "PROCEDENTE"
    And the plaintiff lawyer is "111111/SP"
    And the defendant lawyer is "222222/RJ"
    When I run the analyze command
    Then the winner should be plaintiff lawyer "111111/SP"
    And the loser should be defendant lawyer "222222/RJ"

  Scenario: Identify winner and loser from improcedente sentença
    Given an unanalyzed intimation with PDF
    And the decision is "SENTENÇA" with outcome "IMPROCEDENTE"
    And the plaintiff lawyer is "333333/MG"
    And the defendant lawyer is "444444/SP"
    When I run the analyze command
    Then the winner should be defendant lawyer "444444/SP"
    And the loser should be plaintiff lawyer "333333/MG"

  Scenario: Handle partially favorable decisions (parcialmente procedente)
    Given an unanalyzed intimation with PDF
    And the decision is "PARCIALMENTE PROCEDENTE"
    And the plaintiff lawyer is "555555/RS"
    And the defendant lawyer is "666666/PR"
    When I run the analyze command
    Then the winner should be plaintiff lawyer "555555/RS"
    And the loser should be defendant lawyer "666666/PR"
    And the confidence score should be between 0.6 and 0.8
    And the reasoning should mention "partial victory"

  Scenario: Handle multiple lawyers on the same side
    Given an unanalyzed intimation with PDF
    And the plaintiff is represented by 3 lawyers: "777777/SP", "888888/SP", "999999/SP"
    And the defendant is represented by 1 lawyer: "101010/RJ"
    And the decision is "PROCEDENTE"
    When I run the analyze command
    Then all 3 plaintiff lawyers should be recorded as winners
    And the defendant lawyer "101010/RJ" should be recorded as loser

  Scenario: Extract OAB and state from decision text
    Given an unanalyzed intimation with PDF
    And the decision mentions "Advogado Dr. João Silva, OAB/SP 123.456"
    When I run the analyze command
    Then the system should extract OAB "123456"
    And the system should extract state "SP"
    And the OAB should be stored in normalized format

  # ============================================================================
  # CONFIDENCE SCORING
  # ============================================================================

  Scenario: High confidence for clear, unambiguous decisions
    Given an unanalyzed intimation with PDF
    And the decision clearly states "JULGO PROCEDENTE O PEDIDO"
    And winner and loser are explicitly identified
    And all required fields are present in the PDF
    When I run the analyze command
    Then the confidence score should be above 0.9

  Scenario: Medium confidence for partially clear decisions
    Given an unanalyzed intimation with PDF
    And the decision outcome is clear but lawyer information is implicit
    When I run the analyze command
    Then the confidence score should be between 0.6 and 0.8

  Scenario: Low confidence for ambiguous decisions
    Given an unanalyzed intimation with PDF
    And the decision text is unclear about the outcome
    And lawyer information is missing or incomplete
    When I run the analyze command
    Then the confidence score should be below 0.6
    And a warning should be logged about low confidence

  Scenario: Reject analysis with very low confidence
    Given an unanalyzed intimation with PDF
    And the Gemini model returns confidence below 0.3
    When I run the analyze command
    Then the analysis should not be stored
    And the intimation should remain marked as unanalyzed
    And an error should be logged indicating low confidence rejection

  # ============================================================================
  # BATCH PROCESSING
  # ============================================================================

  Scenario: Analyze multiple intimations in batch
    Given there are 10 unanalyzed intimations
    When I run the analyze command with batch size 5
    Then the system should process 2 batches
    And all 10 intimations should be analyzed
    And each batch should be processed concurrently

  Scenario: Respect max batches limit
    Given there are 50 unanalyzed intimations
    When I run the analyze command with max_batches 3 and batch_size 10
    Then the system should process exactly 30 intimations
    And 20 intimations should remain unanalyzed

  Scenario: Handle concurrent LLM requests efficiently
    Given there are 5 unanalyzed intimations
    When I run the analyze command with batch size 5
    Then all 5 LLM requests should be sent concurrently
    And the total processing time should be close to single-request time
    And all 5 analyses should complete successfully

  # ============================================================================
  # ERROR HANDLING
  # ============================================================================

  Scenario: Retry analysis on transient LLM failures
    Given an unanalyzed intimation with ID "intimacao-retry"
    And the Gemini API returns a temporary error on first call
    When I run the analyze command
    Then the system should retry the request
    And the analysis should succeed after retry

  Scenario: Skip analysis on permanent LLM failures
    Given an unanalyzed intimation with malformed PDF
    And the Gemini API consistently returns validation errors
    When I run the analyze command
    Then the system should log a permanent failure
    And the intimation should remain unanalyzed
    And the error should be recorded in the database

  Scenario: Handle PDF read failures gracefully
    Given an unanalyzed intimation with ID "intimacao-corrupt"
    And the PDF file is corrupted or unreadable
    When I run the analyze command
    Then the system should log a PDF read error
    And the intimation should remain unanalyzed
    And the analysis should continue with other intimations

  Scenario: Validate LLM response structure
    Given an unanalyzed intimation with PDF
    And the Gemini API returns malformed JSON
    When I run the analyze command
    Then the system should reject the malformed response
    And the intimation should remain unanalyzed
    And a validation error should be logged

  # ============================================================================
  # SPECIAL CASES
  # ============================================================================

  Scenario: Handle decisions with no clear winner (extinto sem mérito)
    Given an unanalyzed intimation with PDF
    And the decision is "EXTINTO SEM RESOLUÇÃO DE MÉRITO"
    When I run the analyze command
    Then the outcome should be "EXTINTO SEM RESOLUÇÃO MÉRITO"
    And both winner and loser fields may be empty
    And the confidence score should reflect the lack of clear outcome

  Scenario: Analyze decisão interlocutória (interlocutory decision)
    Given an unanalyzed intimation with PDF
    And the decision type is "DECISÃO INTERLOCUTÓRIA"
    And the decision grants a preliminary injunction
    When I run the analyze command
    Then the decision type should be "DECISÃO INTERLOCUTÓRIA"
    And the winner should be the party who requested the injunction
    And the confidence score should account for non-final nature

  Scenario: Handle appeal reversal correctly
    Given an unanalyzed intimation with "ACÓRDÃO"
    And the appeal outcome is "DAR PROVIMENTO AO RECURSO"
    And the original decision favored the defendant
    When I run the analyze command
    Then the winner should be the appellant (plaintiff)
    And the loser should be the appellee (defendant)
    And the reasoning should mention "appeal granted"

  # ============================================================================
  # INCREMENTAL PROCESSING
  # ============================================================================

  Scenario: Only analyze unanalyzed intimations
    Given the intimations table contains:
      | ID    | Analyzed |
      | int-1 | True     |
      | int-2 | False    |
      | int-3 | False    |
    When I run the analyze command
    Then only intimations "int-2" and "int-3" should be analyzed
    And intimation "int-1" should be skipped

  Scenario: Mark intimation as analyzed after successful analysis
    Given an unanalyzed intimation with ID "intimacao-mark"
    When I run the analyze command
    And the analysis succeeds
    Then the intimation "intimacao-mark" should be marked as analyzed
    And subsequent analyze commands should skip it

  # ============================================================================
  # DATA QUALITY
  # ============================================================================

  Scenario: Validate analysis output completeness
    Given an unanalyzed intimation with PDF
    When I run the analyze command
    And the analysis is stored
    Then the analysis must have a decision type
    And the analysis must have an outcome
    And the analysis must have a confidence score between 0.0 and 1.0
    And the analysis must reference the intimation ID

  Scenario: Normalize state codes in lawyer identification
    Given an unanalyzed intimation with PDF
    And the decision mentions lawyer "OAB/sp 123456" (lowercase state)
    When I run the analyze command
    Then the state should be normalized to "SP" (uppercase)

  Scenario: Store analysis metadata for auditability
    Given an unanalyzed intimation with PDF
    When I run the analyze command
    Then the analysis should record the LLM model used
    And the analysis should record the timestamp
    And the analysis should record the system version
    And the analysis should be fully auditable

  # ============================================================================
  # PERFORMANCE
  # ============================================================================

  Scenario: Process large PDFs efficiently
    Given an unanalyzed intimation with a 50-page PDF
    When I run the analyze command
    Then the analysis should complete within reasonable time (< 30 seconds)
    And the entire PDF content should be analyzed

  Scenario: Handle rate limits from LLM provider
    Given there are 100 unanalyzed intimations
    And the Gemini API has rate limits
    When I run the analyze command
    Then the system should respect rate limits
    And the system should process all intimations without errors
    And the processing should use backoff strategies when needed
