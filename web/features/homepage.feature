Feature: Homepage
  The landing page shows pipeline stats and explains the project.

  Scenario: Display pipeline stats cards
    Given the snapshot has 15000 total ZIPs
    And the snapshot has 85 tribunals with data
    And the snapshot has 120 GB archived
    When the homepage loads
    Then I should see "15K" in the stats section
    And I should see "85" in the tribunals card
    And I should see "120" in the volume card

  Scenario: Show live pipeline card with backfill progress
    Given the pipeline has 75 percent backfill progress
    When the homepage loads
    Then I should see "75%" in the pipeline card

  Scenario: Display all how-it-works cards
    When the homepage loads
    Then I should see "Coleta diária"
    And I should see "Parquet pronto para análise"
    And I should see "Download em massa"

  Scenario: Display all audience cards
    When the homepage loads
    Then I should see "Pesquisadores"
    And I should see "LegalTechs"
    And I should see "Jornalistas"
