Feature: Tribunal Detail
  Individual tribunal page showing detailed coverage and quality metrics.

  Scenario: Show tribunal name and selector
    Given tribunal code is "STF"
    When the tribunal detail page loads
    Then I should see a tribunal selector
    And "STF" should be selected

  Scenario: Render tribunal content after mount
    Given tribunal code is "STJ"
    When the component mounts before hash is parsed
    Then I should see the tribunal name in the detail view

  Scenario: Tribunal selector contains all tribunals
    Given tribunal code is "STF"
    When the tribunal detail page loads
    Then the selector should contain "STJ" as an option
    And the selector should contain "TRT1" as an option
