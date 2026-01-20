Feature: Transparency and Auditability
  As a transparency advocate
  I want complete visibility into how ratings are calculated
  So that I can trust and verify the system's integrity

  Background:
    Given the CausaGanha platform is operational
    And transparency features are enabled

  # ============================================================================
  # NOTE: This feature is PARTIALLY in MVP, fully implemented in Phase 2-3
  # Internet Archive preservation is MVP (P2)
  # Public methodology and audit trails are Public Beta/Launch (Phase 2-3)
  # ============================================================================

  # ============================================================================
  # AUDIT TRAIL - RATINGS TO SOURCE DOCUMENTS
  # ============================================================================

  Scenario: Trace rating back to source data (Parquet data lake)
    Given lawyer "123456/SP" has rating 32.5
    When I view the rating details
    Then I should see all cases that contributed to this rating
    And each case should link to the analysis record
    And each analysis should link to the Parquet partition on Internet Archive
    And I can download the Parquet file and verify the entire chain of evidence

  Scenario: View complete decision analysis
    Given an analyzed decision with ID "ana-001"
    When I view the analysis details
    Then I should see:
      | Field                | Example Value                                  |
      | Intimation ID        | int-12345                                      |
      | Case Number          | 0001234-56.2024.8.22.0001                     |
      | Tribunal             | TJRO                                           |
      | Decision Type        | SENTENÇA                                       |
      | Outcome              | PROCEDENTE                                     |
      | Winner               | 123456/SP (OAB/State)                          |
      | Loser                | 234567/RJ                                      |
      | Judge                | Dr. Carlos Silva                               |
      | Reasoning            | Summary of decision reasoning                  |
      | Confidence           | 0.92                                           |
      | Analyzed Date        | 2025-01-15 14:23:01 UTC                        |
      | LLM Model            | gemini-2.0-flash-exp                           |
      | Parquet File         | causaganha-TJRO-2025-01.parquet                |
      | Archive URL          | https://archive.org/details/causaganha-TJRO-2025-01 |

  Scenario: Download and verify data from Parquet data lake
    Given an analysis identifies lawyer "123456/SP" as winner
    When I download the Parquet file from Internet Archive
    Then I can query the Parquet file with DuckDB
    And I can find the exact row with intimation_id "int-12345"
    And I can verify the winner identification matches
    And I can read the original `texto` field to validate LLM extraction

  Scenario: View rating calculation history
    Given lawyer "123456/SP" has 45 rated cases
    When I view the rating history
    Then I should see a chronological list of all cases
    And each case should show:
      | Field               | Example             |
      | Date                | 2025-01-15          |
      | Outcome             | Win / Loss          |
      | Opponent Rating     | 28.5                |
      | Rating Before       | 32.1                |
      | Rating After        | 32.5                |
      | Rating Change       | +0.4                |
      | Uncertainty Before  | 4.5                 |
      | Uncertainty After   | 4.2                 |

  # ============================================================================
  # METHODOLOGY TRANSPARENCY
  # ============================================================================

  Scenario: Public methodology documentation
    Given I want to understand how ratings work
    When I access the methodology page
    Then I should find comprehensive documentation including:
      | Section                           | Content                                     |
      | Overview                          | High-level explanation in plain language    |
      | Data Collection                   | How decisions are gathered from PJe         |
      | AI Analysis                       | Gemini LLM prompts and extraction process   |
      | Rating Algorithm                  | OpenSkill (PlackettLuce) mathematical model |
      | Confidence Intervals              | How uncertainty is calculated               |
      | Quality Assurance                 | Validation and accuracy testing             |
      | Limitations                       | What the system cannot do                   |

  Scenario: View actual LLM prompts
    Given I want to understand how AI analyzes decisions
    When I view the "AI Analysis" section
    Then I should see the exact system prompt used
    And the prompt should be shown in a code block
    And there should be an example input/output
    And limitations should be explained

  Scenario: Understand OpenSkill algorithm
    Given I want to understand rating calculations
    When I view the "Rating Algorithm" section
    Then I should see:
      | Content                              |
      | Mathematical formula for OpenSkill   |
      | Explanation of mu (skill estimate)   |
      | Explanation of sigma (uncertainty)   |
      | Conservative estimate formula        |
      | Example calculation walkthrough      |
      | Interactive demo (optional)          |

  Scenario: Access methodology as PDF
    Given I want to cite the methodology in research
    When I download the methodology PDF
    Then it should be formatted as an academic paper
    And it should include:
      | Section        | Required Content                |
      | Abstract       | Summary of approach             |
      | Introduction   | Problem statement               |
      | Methods        | Detailed technical description  |
      | Validation     | Accuracy testing results        |
      | Discussion     | Limitations and future work     |
      | References     | Citations (OpenSkill, etc.)     |
    And it should have a version number and date
    And it should be citable with DOI or permalink

  # ============================================================================
  # DATA QUALITY TRANSPARENCY
  # ============================================================================

  Scenario: View accuracy metrics
    Given the system has been validated
    When I access the data quality dashboard
    Then I should see:
      | Metric                          | Example Value |
      | Total analyses                  | 50,000        |
      | Manual validations performed    | 500           |
      | Accuracy rate                   | 92%           |
      | Average confidence score        | 0.85          |
      | Low confidence rate (<0.7)      | 8%            |
      | Rejected analyses (too low)     | 3%            |
    And metrics should be updated monthly

  Scenario: View accuracy over time
    Given accuracy has been tracked for 12 months
    When I view the accuracy trends
    Then I should see a chart showing accuracy by month
    And I should see if accuracy is improving or degrading
    And significant changes should be explained

  Scenario: Download sample validation dataset
    Given I want to verify accuracy claims
    When I click "Download Sample Validation Data"
    Then I should receive a CSV file with:
      | Column              | Description                          |
      | intimation_id       | Unique identifier                    |
      | parquet_file        | Partition file on Internet Archive   |
      | archive_url         | Link to Parquet on archive.org       |
      | llm_winner          | AI-identified winner                 |
      | llm_loser           | AI-identified loser                  |
      | manual_winner       | Human-verified winner                |
      | manual_loser        | Human-verified loser                 |
      | correct             | TRUE/FALSE                           |
      | confidence          | 0.0-1.0                              |
    And I can download the Parquet files to manually verify the texto field

  # ============================================================================
  # CHANGE LOG & VERSIONING
  # ============================================================================

  Scenario: View system changelog
    Given the system has been updated over time
    When I access the changelog
    Then I should see a list of changes by date:
      | Date       | Change                                        | Impact           |
      | 2025-01-15 | Updated LLM model to gemini-2.0-flash-exp     | Improved accuracy|
      | 2025-01-10 | Added 5 new tribunals (TJSP, TJRJ, etc.)      | Expanded coverage|
      | 2025-01-05 | Raised confidence threshold from 0.5 to 0.7   | Higher quality   |

  Scenario: Rating version tracking
    Given lawyer "123456/SP" has been rated over time
    When I view rating history
    Then each rating should include the system version
    And I should know which LLM model was used
    And I should know which OpenSkill parameters were used
    And major version changes should be highlighted

  # ============================================================================
  # INTERNET ARCHIVE PRESERVATION (PARQUET DATA LAKE)
  # ============================================================================

  Scenario: All analyzed decisions exported to Parquet data lake
    Given a decision has been analyzed on January 15, 2025
    When I check its archival status
    Then it must be included in the daily Parquet export for 2025-01-15
    And the Parquet file must have an Internet Archive URL
    And the URL should be publicly accessible (e.g., archive.org/details/causaganha-2025-01-15)
    And I can download and query the Parquet file with DuckDB
    And the decision's texto field should be present for verification

  Scenario: Archive.org Parquet metadata is complete
    Given a daily Parquet partition "causaganha-2025-01-15" has been archived
    When I view the item on archive.org
    Then the metadata should include:
      | Field           | Example Value                                           |
      | Title           | CausaGanha - Brazilian Court Decisions - 2025-01-15     |
      | Collection      | causaganha                                              |
      | Media Type      | data                                                    |
      | Format          | Parquet                                                 |
      | Subject         | judicial decisions; brazil; 2025-01-15                  |
      | Date            | 2025-01-15                                              |
      | Coverage        | Brazil - All Tribunals                                  |
      | Source          | PJe - 90 Brazilian Tribunals                            |
      | Rights          | CC0 1.0 Universal (Public Domain)                       |

  Scenario: Verify Parquet export completeness
    When I query the system for export statistics
    Then I should see:
      | Metric                      | Target    |
      | Total decisions collected   | 8.1M/month|
      | Total decisions exported    | 8.1M/month|
      | Export rate                 | 100%      |
      | Failed exports              | 0         |
      | Parquet partitions created  | 30/month  |
      | Total Parquet size on IA    | ~4 GB/month|
    And any export failures should be listed with reasons

  # ============================================================================
  # DISPUTE & CORRECTION TRANSPARENCY
  # ============================================================================

  Scenario: View dispute history for a rating
    Given lawyer "123456/SP" has disputed one analysis
    When I view the rating details
    Then I should see a dispute indicator
    And I can view the dispute details:
      | Field              | Example                          |
      | Disputed Date      | 2025-01-10                       |
      | Dispute Reason     | Incorrect winner identification  |
      | Status             | Under Review / Resolved          |
      | Resolution         | Confirmed incorrect, corrected   |
      | Rating Impact      | Rating recalculated               |

  Scenario: Correction history is public
    Given an analysis was corrected after dispute
    When I view the analysis details
    Then I should see:
      | Field                  | Value                        |
      | Original Winner        | 123456/SP                    |
      | Corrected Winner       | 234567/RJ                    |
      | Correction Date        | 2025-01-12                   |
      | Correction Reason      | Manual review                |
      | Reviewer               | Data Quality Team            |
    And affected ratings should show "Recalculated on 2025-01-12"

  # ============================================================================
  # STATISTICAL SUMMARIES
  # ============================================================================

  Scenario: National statistics dashboard
    When I access the statistics page
    Then I should see national-level metrics:
      | Metric                          | Example Value    |
      | Total tribunals monitored       | 10               |
      | Total decisions analyzed        | 500,000          |
      | Total lawyers rated             | 50,000           |
      | Average lawyer rating           | 25.0 (by design) |
      | Most active tribunal            | TJSP (5,000/day) |
      | Oldest decision analyzed        | 2023-01-01       |
      | Most recent decision            | 2025-01-18       |
      | Data collection uptime          | 98.5%            |

  Scenario: Per-tribunal statistics
    When I select tribunal "TJRO"
    Then I should see tribunal-specific metrics:
      | Metric                     | Value     |
      | Decisions analyzed         | 15,000    |
      | Lawyers rated              | 3,500     |
      | Average cases per lawyer   | 4.3       |
      | Data collection start date | 2024-06-01|
      | Collection frequency       | Daily     |
      | Last update                | 2025-01-18|

  # ============================================================================
  # OPEN DATA COMMITMENT
  # ============================================================================

  Scenario: API documentation is public
    Given I want to access data programmatically
    When I visit the API documentation page
    Then I should see:
      | Section              | Content                              |
      | Authentication       | How to get API key                   |
      | Rate Limits          | Free tier: 1,000 req/month           |
      | Endpoints            | GET /lawyers, GET /decisions, etc.   |
      | Response Format      | JSON schema with examples            |
      | Error Codes          | List of HTTP status codes            |
    And I can try API calls interactively (Swagger/OpenAPI)

  Scenario: Bulk data export available
    Given I am a researcher
    When I request bulk data export
    Then I should be able to download:
      | Dataset           | Format | Size Estimate |
      | All lawyers       | CSV    | 5 MB          |
      | All analyses      | CSV    | 50 MB         |
      | All ratings       | CSV    | 10 MB         |
    And data should be anonymized (no lawyer names, just OAB/state)
    And a data dictionary should be included

  Scenario: License and attribution
    When I access the data
    Then the license should be clearly stated:
      | License Aspect    | Value                                    |
      | Data License      | CC0 (Public Domain) or ODbL              |
      | Attribution       | "Data from CausaGanha (causaganha.org)"  |
      | Restrictions      | None (open data)                         |
    And proper citation format should be provided

  # ============================================================================
  # TRANSPARENCY FOR LAWYERS
  # ============================================================================

  Scenario: Lawyer views their own rating details
    Given I am lawyer "123456/SP"
    When I verify my identity (OAB lookup or email verification)
    Then I should see my complete rating details
    And I should see all cases that contributed to my rating
    And I can download a PDF report of my performance
    And I can see how I compare to average lawyers in my area

  Scenario: Lawyer understands rating components
    Given I am viewing my rating details
    Then I should see a breakdown:
      | Component                   | Value    | Explanation                    |
      | Skill Estimate (mu)         | 32.5     | Your estimated skill level     |
      | Uncertainty (sigma)         | 4.2      | How certain we are (lower better)|
      | Conservative Rating         | 19.9     | mu - 3*sigma (displayed rating)|
      | Total Matches               | 45       | Cases that affected rating     |
      | Win Rate                    | 68%      | Percentage of wins             |
      | Percentile Rank             | Top 15%  | Compared to all lawyers        |

  # ============================================================================
  # REPRODUCIBILITY
  # ============================================================================

  Scenario: Reproduce rating calculation
    Given I have lawyer "123456/SP" rating data
    And I have the list of all their cases with outcomes
    And I have the OpenSkill algorithm parameters
    When I manually calculate the rating using the formula
    Then my calculated rating should match the system rating
    And this proves the rating is deterministic and reproducible

  Scenario: Validate LLM analysis
    Given I have a decision's texto field from the Parquet data lake
    And I have the LLM prompt and model version
    When I send the same texto to Gemini with the same prompt
    Then I should get a consistent analysis result
    And I can verify the system's analysis is reproducible

  # ============================================================================
  # THIRD-PARTY VERIFICATION
  # ============================================================================

  Scenario: Independent audit support
    Given an external auditor wants to verify our methodology
    When they request access to validation data
    Then we should provide:
      | Resource                         | Purpose                          |
      | Random sample of 1000 decisions  | Manual re-analysis (texto field) |
      | Parquet data lake access         | Download and verify source data  |
      | Corresponding LLM analyses       | Compare to their analysis        |
      | Rating calculation scripts       | Verify OpenSkill implementation  |
      | Accuracy testing results         | Validate our accuracy claims     |

  Scenario: Academic research access
    Given a researcher wants to use our data
    When they contact us for research access
    Then we should provide:
      | Resource                | Access Level        |
      | Full dataset (anonymized)| Free download       |
      | API access              | Elevated rate limits|
      | Methodology consultation | Email support       |
      | Co-authorship           | For significant studies|

  # ============================================================================
  # LIMITATIONS TRANSPARENCY
  # ============================================================================

  Scenario: Clearly communicate limitations
    Given I am reading about the platform
    When I access the "Limitations" section
    Then I should see honest disclaimers:
      | Limitation                                     |
      | Ratings reflect case outcomes, not case quality|
      | Cannot account for case difficulty             |
      | New lawyers have high uncertainty              |
      | Missing data for some tribunals/periods        |
      | LLM analysis has 8-15% error rate              |
      | Partial victories treated as wins              |
      | Team cases credit all lawyers equally (simplified)|

  Scenario: Uncertainty is always shown
    When viewing any lawyer rating
    Then the uncertainty (confidence interval) must be displayed
    And low-confidence ratings should have warning badges
    And explanations should clarify what uncertainty means
