Feature: Consolidation Checkpointing
  As a data engineer
  I want consolidation to checkpoint progress during backfill
  So that I can resume from where I left off after an interruption

  Scenario: Consolidation saves checkpoint after checking dates
    Given a clean environment with no backfill checkpoint
    When I find the next unconsolidated date
    Then the checkpoint file should be created
    And the checkpoint should contain the last date checked

  Scenario: Consolidation resumes from last checkpoint
    Given a checkpoint exists for 5 days ago
    When I find the next unconsolidated date
    Then it should skip checking dates from the last 4 days
    And resume scanning from 5 days ago
