Feature: Transform DJEN records into 10 normalized Parquet tables
  As the consolidation pipeline
  I want to parse DJEN ZIP contents into well-typed tables
  So analytics can query uniform facts across all tribunals

  Scenario: One record with 2 parties and 2 lawyers populates all relevant tables
    Given a synthetic NDJSON record with a WIN outcome
    And that record has 2 parties and 2 lawyers
    When I run the transform for item_id djen-tjsp-2026
    Then comunicacoes has 1 row
    And destinatarios has 2 rows
    And advogados has 2 rows
    And textos has 1 row
    And classificacoes has 1 row
    And the classificacoes outcome is WIN

  Scenario: Record with IMPROCEDENTE classifies as LOSS
    Given a synthetic NDJSON record with an improcedente verdict
    When I run the transform for item_id djen-tjrs-2026
    Then the classificacoes outcome is LOSS
