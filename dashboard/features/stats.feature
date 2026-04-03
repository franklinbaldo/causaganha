Feature: Statistics Page
  Historical coverage and reliability analysis of tribunal data collection.

  Scenario: Show coverage overview cards
    Given completed items data with 30 days of collection
    And the average daily coverage is 78 out of 91
    When the stats page renders
    Then I should see the average coverage percentage
    And I should see the best and worst collection days

  Scenario: Show court reliability rankings
    Given completed items data with tribunal performance
    When the stats page renders
    Then I should see "Mais Confiáveis" section with top courts
    And I should see "Mais Falhas" section with bottom courts

  Scenario: Show weekly collection pattern
    Given completed items data with 30 days of collection
    When the stats page renders
    Then I should see all 7 days of the week
    And each day should show an average coverage percentage
