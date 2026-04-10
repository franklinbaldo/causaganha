Feature: Publications Overview
  The publications page shows an interactive overview of all tribunal data.

  Scenario: Show archive progress banner
    Given the IA snapshot has 15000 total ZIPs
    And 85 tribunals have data
    When the publications overview loads
    Then I should see "Progresso do Arquivo"
    And I should see the ZIP count in the banner
    And I should see "85" as tribunals with data

  Scenario: Show tribunal cards in the grid
    Given coverage data for tribunals STF and STJ
    When the publications overview loads
    Then I should see a card for "STF"
    And I should see a card for "STJ"

  Scenario: Show group headings for tribunal branches
    When the publications overview loads with default data
    Then I should see "Tribunais Superiores"
    And I should see "Justiça Federal"
    And I should see "Justiça Estadual"

  Scenario: Show ZIP counts per tribunal
    Given STF has 150 ZIPs in the snapshot
    When the publications overview loads
    Then I should see "150" next to STF
