Feature: RAG Integration in CLI
  As a command-line user,
  I want to control RAG analysis via CLI commands,
  So that I can choose the optimal analysis strategy for my use case.

  Background:
    Given the CausaGanha CLI is installed
    And the database is initialized with test data

  Scenario: Analyze decisions using default hybrid strategy
    Given there are 5 pending decisions in the database
    When I run "causaganha analyze --limit 5"
    Then 5 decisions should be analyzed
    And the hybrid strategy should be used by default
    And the output should show cost savings statistics

  Scenario: Analyze decisions using RAG-only strategy
    Given there are 10 pending decisions in the database
    When I run "causaganha analyze --strategy rag --limit 10"
    Then 10 decisions should be analyzed using RAG only
    And no LLM calls should be made
    And the total cost should be approximately $0.00008

  Scenario: Analyze decisions using LLM-only strategy
    Given there are 3 pending decisions in the database
    When I run "causaganha analyze --strategy llm --limit 3"
    Then 3 decisions should be analyzed using LLM only
    And no RAG calls should be made
    And the total cost should be approximately $0.00126

  Scenario: Configure custom confidence threshold
    Given there are 5 pending decisions in the database
    When I run "causaganha analyze --strategy hybrid --confidence-threshold 0.80 --limit 5"
    Then the confidence threshold should be set to 0.80
    And decisions with RAG confidence below 0.80 should use LLM fallback

  Scenario: Initialize ground truth from high-confidence results
    Given there are 100 analyzed decisions with confidence >= 0.90
    When I run "causaganha groundtruth init --min-confidence 0.90 --limit 100"
    Then 100 decisions should be exported as ground truth
    And the ground truth file should be created

  Scenario: Index ground truth into vector store
    Given a ground truth file exists with 50 decisions
    When I run "causaganha groundtruth index"
    Then the vector store should be created
    And 50 decisions should be indexed with embeddings
    And the index metadata should be saved

  Scenario: Validate RAG accuracy against ground truth
    Given the vector store is indexed with ground truth
    And there are test decisions with known outcomes
    When I run "causaganha groundtruth validate"
    Then the accuracy report should be displayed
    And the accuracy should be calculated against known outcomes
    And confusion matrix should be shown

  Scenario: Expand ground truth dataset
    Given the current ground truth has 50 decisions
    When I run "causaganha groundtruth expand --target 200"
    Then the system should identify 150 additional high-confidence decisions
    And the ground truth should be expanded to 200 decisions
    And the vector store should be re-indexed

  Scenario: View analysis statistics
    Given 100 decisions have been analyzed with hybrid strategy
    When I run "causaganha stats analyze"
    Then the output should show total decisions analyzed
    And the RAG usage rate should be displayed
    And the LLM fallback rate should be displayed
    And the total cost and cost per decision should be shown
    And the average confidence score should be displayed

  Scenario: CLI help shows strategy options
    When I run "causaganha analyze --help"
    Then the help text should describe the --strategy option
    And the available strategies should be listed: llm, rag, hybrid, auto
    And the default strategy should be indicated as hybrid
    And the --confidence-threshold option should be documented
