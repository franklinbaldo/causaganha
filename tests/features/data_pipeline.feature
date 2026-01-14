Feature: Data Pipeline
  As a user,
  I want to run the data pipeline,
  So that I can process judicial data.

  Scenario: Initialize the database
    Given the system is in a clean state
    When I initialize the database
    Then the database should be created with the correct schema
