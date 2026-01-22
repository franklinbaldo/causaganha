Feature: Structured Text Sections in Parquet (P1 - High Priority)
  As a legal data analyst
  I want decision text split into structured sections (facts, reasoning, decision)
  So that RAG accuracy improves by 10-15% and LLM processing is 30-40% faster

  Background:
    Given the system supports text section extraction
    And extraction methods include "llm" and "heuristic"

  @p1 @sections @export-llm
  Scenario: Export parquet with LLM-extracted sections
    Given I have 100 analyzed decisions with full texto
    And I configure section extraction method as "llm"
    When I export to parquet with schema v2
    Then the parquet file should contain a "texto_sections" struct column
    And each struct should have "full_text", "facts", "reasoning", "decision", "metadata" fields
    And the "extracted_method" field should be "llm"
    And the extraction cost should be approximately $0.01 (100 × $0.0001)
    And the file size should increase by approximately 5-10%

  @p1 @sections @export-heuristic
  Scenario: Export parquet with heuristic-extracted sections
    Given I have 1000 analyzed decisions with full texto
    And I configure section extraction method as "heuristic"
    When I export to parquet with schema v2
    Then the parquet file should contain structured sections
    And the "extracted_method" field should be "heuristic"
    And the extraction should complete in less than 5 seconds
    And the extraction cost should be $0.00 (free)
    And approximately 70-80% of decisions should have all sections populated

  @p1 @sections @hybrid-extraction
  Scenario: Hybrid extraction - heuristic with LLM fallback
    Given I have 1000 analyzed decisions
    And I configure section extraction method as "hybrid"
    When I export to parquet with schema v2
    Then the system should try heuristic extraction first
    And for decisions where heuristic fails, use LLM extraction
    And approximately 20-30% should use LLM extraction
    And the total cost should be $0.02-0.03 (200-300 × $0.0001)

  @p1 @sections @validation
  Scenario: Validate section extraction quality
    Given I have a parquet file with structured sections
    When I read 100 decisions from the parquet file
    Then at least 95% should have non-empty "decision" section
    And at least 80% should have non-empty "facts" section
    And at least 85% should have non-empty "reasoning" section
    And the sum of section lengths should approximately equal full_text length

  @p1 @sections @rag-analysis
  Scenario: RAG analysis using structured sections for better accuracy
    Given I have a parquet file with structured sections
    And I configure RAG to embed only "decision" sections
    When I analyze 100 decisions using RAG
    Then the RAG accuracy should improve by 10-15% compared to full text
    And the confidence scores should be higher on average
    And the analysis should focus on the most relevant text

  @p1 @sections @llm-analysis
  Scenario: LLM analysis using specific sections for efficiency
    Given I have a parquet file with structured sections
    And I configure LLM to analyze only "facts" and "decision" sections
    When I analyze 50 decisions using LLM
    Then the LLM processing time should be 30-40% faster
    And the token usage should be reduced by 30-40%
    And the accuracy should remain the same or improve

  @p1 @sections @section-specific-embeddings
  Scenario: Generate embeddings per section for specialized search
    Given I have a parquet file with structured sections
    When I generate embeddings for each section type
    Then I should have separate embeddings for "facts", "reasoning", "decision"
    And I can search for similar decisions based on specific sections
    And legal reasoning similarity search should use only "reasoning" embeddings

  @p1 @sections @brazilian-legal-patterns
  Scenario: Heuristic extraction recognizes Brazilian legal document structure
    Given I have a typical Brazilian sentença with standard sections
    And the text contains "RELATÓRIO", "FUNDAMENTAÇÃO", "DISPOSITIVO" markers
    When I apply heuristic section extraction
    Then "RELATÓRIO" content should be extracted as "facts"
    And "FUNDAMENTAÇÃO" content should be extracted as "reasoning"
    And "DISPOSITIVO" content should be extracted as "decision"
    And the extraction should be 95%+ accurate for standard format documents

  @p1 @sections @edge-cases
  Scenario Outline: Handle edge cases in section extraction
    Given I have a decision with <edge_case>
    When I extract sections using <method>
    Then the extraction should <result>
    And the system should log <log_level> message

    Examples:
      | edge_case                     | method     | result                          | log_level |
      | no clear section markers      | heuristic  | fallback to full_text           | warning   |
      | very short decision (< 500 chars) | llm   | extract with low confidence     | info      |
      | malformed structure           | hybrid     | use LLM after heuristic fails   | info      |
      | multiple dispositivo sections | heuristic  | concatenate all decision parts  | debug     |
      | missing relatório section     | heuristic  | leave facts empty               | debug     |

  @p1 @sections @backward-compatibility
  Scenario: Schema v1 files without sections still work
    Given I have a schema v1 parquet file without structured sections
    When I analyze decisions from the v1 file
    Then the system should use the "texto" field directly
    And the analysis should complete successfully
    And a warning should be logged about missing sections

  @p1 @sections @quality-metrics
  Scenario: Track section extraction quality metrics
    Given I export 1000 decisions with section extraction
    When I review the extraction statistics
    Then I should see the percentage of successful extractions per section
    And I should see the average section lengths
    And I should see the distribution of extraction methods used
    And I should see the total extraction cost
