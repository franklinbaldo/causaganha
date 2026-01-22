Feature: Multi-Parquet Architecture with DuckDB Joins
  As a data architect
  I want decisions, lawyers, and partes in separate parquet files
  So that I can optimize storage and query efficiency with DuckDB joins

  Background:
    Given the system exports to multiple parquet files:
      | file_type | example_filename                    |
      | decisions | causaganha-decisions-2025-01-15-TJRO.parquet |
      | lawyers   | causaganha-lawyers-2025-01-15.parquet        |
      | partes    | causaganha-partes-2025-01-15-TJRO.parquet    |
    And DuckDB can join parquet files at query time

  @architecture @decisions-parquet @schema-v2
  Scenario: Decisions parquet contains analysis data and embeddings (NOT lawyer details)
    Given I export decisions for date "2025-01-15" tribunal "TJRO"
    When I create the decisions parquet file
    Then it should contain:
      | field_group            | fields                                                    |
      | Identifiers            | intimation_id, numero_processo, hash, tribunal           |
      | Decision text          | texto, texto_sections (P1)                                |
      | Embeddings             | texto_embedding, embedding_model, embedding_generated_at (P0) |
      | Analysis results       | winner_lawyer_oab, loser_lawyer_oab, outcome, decision_type |
      | Confidence             | confidence_breakdown (P2)                                 |
      | Metadata               | analyzed_at, analysis_method                              |
    But it should NOT contain:
      | excluded_fields        |
      | lawyer names           |
      | lawyer ratings         |
      | lawyer statistics      |
      | partes details         |

  @architecture @lawyers-parquet
  Scenario: Lawyers parquet contains current ratings and profiles
    Given I export lawyer data for date "2025-01-15"
    When I create the lawyers parquet file
    Then it should contain:
      | field_group     | fields                                                        |
      | Identifiers     | oab_number, oab_state                                         |
      | Profile         | lawyer_name, registration_date                                |
      | Global ratings  | global_rating, global_sigma, global_rank, global_percentile  |
      | Statistics      | total_cases, wins, losses, win_rate                          |
      | Per-tribunal    | tribunal, tribunal_rating, tribunal_sigma, tribunal_cases    |
    And it should be partitioned by oab_state
    And it should include ratings snapshot at export date

  @architecture @partes-parquet
  Scenario: Partes parquet contains case parties information
    Given I export partes data for date "2025-01-15" tribunal "TJRO"
    When I create the partes parquet file
    Then it should contain:
      | field_group     | fields                                            |
      | Identifiers     | intimation_id, numero_processo                   |
      | Parties         | parte_nome, parte_tipo (autor/reu), parte_cpf   |
      | Lawyers         | lawyer_oab, lawyer_state, polo                   |
    And it should enable linking decisions to parties

  @architecture @duckdb-join @enriched-query
  Scenario: Join decisions with lawyers at query time for enriched analysis
    Given I have decisions parquet: "s3://ia/causaganha-decisions-2025-01-15-TJRO.parquet"
    And I have lawyers parquet: "s3://ia/causaganha-lawyers-2025-01-15.parquet"
    When I run DuckDB query:
      ```sql
      SELECT
        d.numero_processo,
        d.outcome,
        d.confidence_breakdown,
        w.lawyer_name AS winner_name,
        w.global_rating AS winner_rating,
        l.lawyer_name AS loser_name,
        l.global_rating AS loser_rating
      FROM 's3://ia/causaganha-decisions-2025-01-15-TJRO.parquet' d
      LEFT JOIN 's3://ia/causaganha-lawyers-2025-01-15.parquet' w
        ON d.winner_lawyer_oab = w.oab_number
        AND d.winner_lawyer_state = w.oab_state
      LEFT JOIN 's3://ia/causaganha-lawyers-2025-01-15.parquet' l
        ON d.loser_lawyer_oab = l.oab_number
        AND d.loser_lawyer_state = l.oab_state
      WHERE w.global_rating < l.global_rating - 100
      ```
    Then I should get all upset victories with full lawyer context
    And the query should complete in less than 5 seconds
    And DuckDB should use efficient columnar joins

  @architecture @benefits @separation
  Scenario: Benefits of separate parquet files
    Given the multi-parquet architecture
    Then I should see these benefits:
      | benefit                  | explanation                                          |
      | Storage efficiency       | Lawyer data stored once, not duplicated per decision |
      | Update flexibility       | Can update lawyer ratings without touching decisions |
      | Query optimization       | DuckDB only loads needed columns                     |
      | Logical separation       | Clear boundaries between entities                    |
      | Reusability             | Lawyer parquet can be used independently             |

  @architecture @storage-comparison
  Scenario: Compare storage sizes - monolithic vs multi-parquet
    Given I have 10000 decisions with 2000 unique lawyers
    When I calculate storage for monolithic approach (lawyer data in decisions)
    Then decisions file size would be: 500 MB (with duplicated lawyer data)
    When I calculate storage for multi-parquet approach
    Then decisions file size would be: 250 MB (without lawyer data)
    And lawyers file size would be: 5 MB (lawyers only, no duplication)
    And total storage would be: 255 MB (49% savings!)

  @architecture @recommended-schema-v2 @decisions-only
  Scenario: Revised Schema v2 recommendation for decisions parquet
    Given the multi-parquet architecture
    When I design schema v2 for decisions parquet
    Then I should include:
      | priority | feature                  | reason                                    |
      | P0       | Pre-computed embeddings  | Can't compute on-the-fly efficiently     |
      | P1       | Structured text sections | Can't extract on-the-fly efficiently     |
      | P2       | Confidence breakdown     | Analysis-specific, can't join from elsewhere |
    But I should EXCLUDE:
      | excluded_feature        | reason                                   |
      | Lawyer enrichment       | Already in lawyers parquet, join at query time |
      | Partes details          | Already in partes parquet                |

  @architecture @historical-snapshots @lawyers
  Scenario: Lawyers parquet provides historical rating snapshots
    Given I export lawyers parquet daily
    And I store: causaganha-lawyers-2025-01-15.parquet, causaganha-lawyers-2025-01-20.parquet
    When I want to track how lawyer "5733" rating changed
    Then I join decisions from 2025-01-15 with lawyers-2025-01-15.parquet (rating then)
    And I join decisions from 2025-01-15 with lawyers-2025-01-20.parquet (rating later)
    And I can calculate rating change: +25.3 points over 5 days

  @architecture @query-patterns @common
  Scenario Outline: Common query patterns with multi-parquet architecture
    Given I have decisions, lawyers, and partes parquets
    When I want to <query_goal>
    Then I run <query_pattern>

    Examples:
      | query_goal                        | query_pattern                                |
      | Find upset victories              | JOIN decisions + lawyers, WHERE winner_rating < loser_rating |
      | Analyze by experience             | JOIN decisions + lawyers, GROUP BY total_cases_bracket |
      | Find cases with specific parties  | JOIN decisions + partes, WHERE parte_nome LIKE '%'      |
      | Calculate tribunal-specific stats | JOIN decisions + lawyers ON tribunal, GROUP BY tribunal |
      | Track lawyer rating over time     | JOIN multiple lawyers parquets by date                 |

  @architecture @partitioning @optimization
  Scenario: Optimize parquet files with appropriate partitioning
    Given I export parquet files to Internet Archive
    When I partition decisions by: date + tribunal
    And I partition lawyers by: oab_state
    And I partition partes by: date + tribunal
    Then DuckDB queries can use partition pruning
    And queries like "WHERE tribunal = 'TJRO'" skip other tribunal files
    And queries like "WHERE oab_state = 'RO'" skip other state lawyers
    And query performance improves 10-50x for filtered queries

  @architecture @schema-v2-revised @file-sizes
  Scenario: Revised schema v2 file sizes without lawyer enrichment
    Given I export 10000 decisions with schema v2 (decisions only)
    When I measure file sizes with schema v2 features:
      | feature              | size_impact |
      | Base data            | 40 MB       |
      | Embeddings (P0)      | +40 MB      |
      | Sections (P1)        | +2 MB       |
      | Confidence (P2)      | +0.2 MB     |
      | Total                | 82.2 MB     |
    Then decisions file is 82.2 MB (NOT 92 MB because no lawyer enrichment!)
    And total multi-parquet storage is: 82.2 MB (decisions) + 5 MB (lawyers) = 87.2 MB
    And this is 15% smaller than monolithic approach with enrichment!

  @architecture @duckdb-performance
  Scenario: DuckDB join performance is fast enough for real-time queries
    Given I have 1 million decisions in parquet
    And I have 50000 unique lawyers in parquet
    When I run a complex join query with aggregations
    Then DuckDB should complete in less than 10 seconds
    And the join overhead is negligible compared to benefits
    And columnar format enables efficient joins
