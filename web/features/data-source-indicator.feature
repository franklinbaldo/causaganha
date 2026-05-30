Feature: Data source indicator
  The data source indicator renders live archive status safely.

  Scenario: Escape HTML characters from generated_at payload
    Given the Internet Archive metadata has generated_at with HTML characters
    When the data source indicator probes the metadata
    Then the generated_at HTML should be displayed as text
    And the live pulse should be rendered as a span
