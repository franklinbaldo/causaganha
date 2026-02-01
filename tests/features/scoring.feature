Feature: Openskill Scoring Logic
  As a developer
  I want to calculate skill ratings for lawyers/teams
  So that I can rank them based on their case performance

  Scenario: Initialize OpenSkill model with default parameters
    When I request a default OpenSkill model
    Then the model should be a PlackettLuce instance
    And the model mu should be 25.0
    And the model sigma should be 8.333

  Scenario: Initialize OpenSkill model with custom parameters
    Given a configuration with mu 30.0 and sigma 5.0
    When I request an OpenSkill model with this configuration
    Then the model mu should be 30.0
    And the model sigma should be 5.0

  Scenario: Create a default rating for a player
    Given a default OpenSkill model
    When I create a rating for "Player1"
    Then the rating should have the model's default mu
    And the rating should have the model's default sigma
    And the rating name should be "Player1"

  Scenario: Create a custom rating for a player
    Given a default OpenSkill model
    When I create a rating for "Player2" with mu 30.0 and sigma 2.0
    Then the rating mu should be 30.0
    And the rating sigma should be 2.0

  Scenario: Update ratings after a win
    Given a default OpenSkill model
    And a player "Winner" with default rating
    And a player "Loser" with default rating
    When the "Winner" wins against "Loser"
    Then the "Winner" rating mu should increase
    And the "Loser" rating mu should decrease

  Scenario: Update ratings after a draw
    Given a default OpenSkill model
    And a player "P1" with default rating
    And a player "P2" with default rating
    When "P1" and "P2" draw
    Then the rating difference between "P1" and "P2" should be negligible

  Scenario: Handle invalid match results
    Given a default OpenSkill model
    And a player "P1" with default rating
    And a player "P2" with default rating
    When I attempt to rate them with an invalid result "invalid_result"
    Then a ValueError should be raised
