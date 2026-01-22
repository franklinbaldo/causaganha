Feature: Time-Travel Queries for Historical Analysis
  As a legal data analyst
  I want to compare parquet snapshots across different time periods
  So that I can track changes in decisions, ratings, and outcomes over time

  Background:
    Given parquet files are exported daily to Internet Archive
    And each file represents a snapshot at a specific date
    And I can query multiple snapshots to see how data evolved
    And common pattern: causaganha-TYPE-YYYY-MM-DD-TRIBUNAL.parquet

  @time-travel @decisions @outcome-changes
  Scenario: Track how decision outcomes change after appeals
    Given I have decisions parquet for "2025-01-15" (original decisions)
    And I have decisions parquet for "2025-03-15" (2 months later)
    When I run time-travel query:
      ```sql
      SELECT
        d1.numero_processo,
        d1.outcome AS outcome_jan,
        d2.outcome AS outcome_mar,
        CASE
          WHEN d1.outcome != d2.outcome THEN 'CHANGED'
          ELSE 'STABLE'
        END AS change_status
      FROM 's3://ia/decisions-2025-01-15-TJRO.parquet' d1
      INNER JOIN 's3://ia/decisions-2025-03-15-TJRO.parquet' d2
        ON d1.numero_processo = d2.numero_processo
      WHERE d1.outcome != d2.outcome
      ```
    Then I should see cases where outcomes changed (appeals, corrections)
    And I can analyze: "What percentage of decisions were reversed?"
    And identify patterns: "Which tribunals have highest reversal rates?"

  @time-travel @lawyers @rating-evolution
  Scenario: Track lawyer rating changes over time
    Given I have lawyer parquet snapshots for each day in January 2025
    When I query rating evolution for lawyer "5733":
      ```sql
      SELECT
        partition_date,
        oab_number,
        global_rating,
        global_rank,
        total_cases,
        win_rate
      FROM read_parquet('s3://ia/lawyers-2025-01-*.parquet')
      WHERE oab_number = '5733'
      ORDER BY partition_date
      ```
    Then I should see daily rating changes
    And I can plot: "Rating went from 1450 to 1520 (+70 points)"
    And identify: "Big jump on 2025-01-15 after winning 3 high-stakes cases"

  @time-travel @quality @confidence-trends
  Scenario: Analyze confidence score trends over time
    Given I export decisions daily with confidence scores
    When I want to see if analysis quality is improving
    Then I run:
      ```sql
      SELECT
        partition_date,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        AVG(confidence_breakdown.winner_identification) AS avg_winner_conf,
        AVG(confidence_breakdown.outcome_classification) AS avg_outcome_conf,
        COUNT(*) AS decisions
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      WHERE sigla_tribunal = 'TJRO'
      GROUP BY partition_date
      ORDER BY partition_date
      ```
    And I should visualize:
      | date | avg_confidence | trend |
      | 2025-01-01 | 0.68 | Baseline |
      | 2025-01-15 | 0.75 | +10% improvement |
      | 2025-01-31 | 0.82 | +20% improvement (model update!) |
    And identify: "Quality improved after deploying new model on 2025-01-15"

  @time-travel @embeddings @model-comparison
  Scenario: Compare embedding quality across model versions
    Given I have embeddings from jina-v3 for 2025-01-15
    And I regenerated embeddings with jina-v4 for the same date
    When I want to compare embedding quality
    Then I can query both versions:
      ```sql
      SELECT
        d.intimation_id,
        d.texto,
        e3.texto_embedding AS jina_v3_emb,
        e4.texto_embedding AS jina_v4_emb
      FROM 's3://ia/decisions-2025-01-15-TJRO.parquet' d
      LEFT JOIN 's3://ia/embeddings-jina-v3-2025-01-15-TJRO.parquet' e3
        ON d.intimation_id = e3.intimation_id
      LEFT JOIN 's3://ia/embeddings-jina-v4-2025-01-15-TJRO.parquet' e4
        ON d.intimation_id = e4.intimation_id
      LIMIT 1000
      ```
    And run A/B test: "Which model has better RAG accuracy?"
    And calculate: "jina-v4 improves recall by 15%"

  @time-travel @partes @party-litigation-history
  Scenario: Track how often specific parties appear in cases over time
    Given I have partes parquet for entire year 2024
    When I want to see litigation frequency for party "BANCO XYZ"
    Then I query:
      ```sql
      SELECT
        DATE_TRUNC('month', partition_date) AS month,
        COUNT(DISTINCT numero_processo) AS cases,
        SUM(CASE WHEN parte_tipo = 'autor' THEN 1 ELSE 0 END) AS as_plaintiff,
        SUM(CASE WHEN parte_tipo = 'reu' THEN 1 ELSE 0 END) AS as_defendant
      FROM read_parquet('s3://ia/partes-2024-*.parquet')
      WHERE parte_nome LIKE '%BANCO XYZ%'
      GROUP BY month
      ORDER BY month
      ```
    And I can see: "BANCO XYZ was defendant in 1200 cases in 2024"
    And trends: "Litigation increased 30% in Q4 2024"

  @time-travel @schema @evolution-tracking
  Scenario: Detect schema changes across parquet versions
    Given I export parquet files with schema v1 until 2025-01-15
    And I upgrade to schema v2 starting 2025-01-16
    When I query both versions
    Then the system should detect schema differences:
      | v1_columns | v2_new_columns |
      | texto | texto_sections (NEW in v2) |
      | confidence_score | confidence_breakdown (NEW in v2) |
      | - | texto_embedding (NEW in v2) |
    And I can handle both schemas:
      ```sql
      SELECT
        intimation_id,
        texto,
        COALESCE(confidence_breakdown.overall, confidence_score) AS confidence
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      ```
    And backward compatibility is maintained

  @time-travel @analysis @reanalysis-impact
  Scenario: Measure impact of reanalysis on historical data
    Given I reanalyzed 2025-01-10 decisions on 2025-01-20 with better model
    And I have both original and reanalyzed versions
    When I compare:
      ```sql
      WITH original AS (
        SELECT * FROM 's3://ia/decisions-2025-01-10-TJRO.parquet'
      ),
      reanalyzed AS (
        SELECT * FROM 's3://ia/decisions-2025-01-10-v2-TJRO.parquet'
      )
      SELECT
        o.intimation_id,
        o.outcome AS original_outcome,
        r.outcome AS reanalyzed_outcome,
        o.confidence_score AS original_confidence,
        r.confidence_breakdown.overall AS reanalyzed_confidence
      FROM original o
      INNER JOIN reanalyzed r ON o.intimation_id = r.intimation_id
      WHERE o.outcome != r.outcome
      ```
    Then I can measure:
      | metric | result |
      | Outcomes changed | 23 out of 10000 (0.23%) |
      | Avg confidence improved | 0.68 → 0.82 (+20%) |
      | Low confidence fixed | 150 decisions now > 0.80 |
    And validate: "Reanalysis was worth it!"

  @time-travel @tribunal @performance-comparison
  Scenario: Compare tribunal performance over quarters
    Given I have decisions for all tribunals for 2024
    When I want to compare Q1 vs Q4 performance by tribunal
    Then I run:
      ```sql
      SELECT
        sigla_tribunal,
        CASE
          WHEN partition_date < '2024-04-01' THEN 'Q1'
          WHEN partition_date >= '2024-10-01' THEN 'Q4'
        END AS quarter,
        COUNT(*) AS decisions,
        AVG(confidence_breakdown.overall) AS avg_confidence
      FROM read_parquet('s3://ia/decisions-2024-*.parquet')
      WHERE partition_date < '2024-04-01'
         OR partition_date >= '2024-10-01'
      GROUP BY sigla_tribunal, quarter
      ORDER BY sigla_tribunal, quarter
      ```
    And I can compare:
      | tribunal | Q1_decisions | Q4_decisions | change |
      | TJRO | 8000 | 12000 | +50% |
      | TJSP | 50000 | 48000 | -4% |
    And identify trends by tribunal

  @time-travel @cost @savings-tracking
  Scenario: Track cost savings from schema improvements over time
    Given I deployed schema v2 with cached embeddings on 2025-01-15
    When I compare costs before and after
    Then I calculate:
      ```sql
      WITH v1_period AS (
        SELECT
          COUNT(*) AS decisions,
          COUNT(*) * 0.00008 AS embedding_cost
        FROM read_parquet('s3://ia/decisions-2025-01-01-*.parquet')
        WHERE partition_date < '2025-01-15'
      ),
      v2_period AS (
        SELECT
          COUNT(*) AS decisions,
          0 AS embedding_cost  -- Embeddings cached!
        FROM read_parquet('s3://ia/decisions-2025-01-15-*.parquet')
        WHERE partition_date >= '2025-01-15'
      )
      SELECT
        v1.embedding_cost AS v1_cost,
        v2.embedding_cost AS v2_cost,
        v1.embedding_cost - v2.embedding_cost AS savings
      FROM v1_period v1, v2_period v2
      ```
    And measure: "Saved $1,200 in embedding costs in January!"

  @time-travel @backfill @historical-gaps
  Scenario: Identify and fill gaps in historical data
    Given I started exporting parquet in 2025-01-01
    And some dates are missing (holidays, system downtime)
    When I run gap detection query:
      ```sql
      WITH date_series AS (
        SELECT DATE '2025-01-01' + INTERVAL (n) DAY AS expected_date
        FROM generate_series(0, 365) AS t(n)
      ),
      exported_dates AS (
        SELECT DISTINCT partition_date
        FROM read_parquet('s3://ia/decisions-2025-*.parquet')
      )
      SELECT d.expected_date
      FROM date_series d
      LEFT JOIN exported_dates e ON d.expected_date = e.partition_date
      WHERE e.partition_date IS NULL
      ORDER BY d.expected_date
      ```
    Then I can identify missing dates: [2025-01-05, 2025-02-14, ...]
    And backfill: causaganha export backfill --dates 2025-01-05,2025-02-14
    And ensure complete historical coverage

  @time-travel @audit @data-lineage
  Scenario: Track data lineage for compliance and auditing
    Given each parquet export includes metadata:
      | metadata_field | example |
      | exported_at | 2025-01-15T03:00:00Z |
      | analysis_version | v2.3.0 |
      | schema_version | v2 |
      | source_system | PJe TJRO |
    When I need to audit a specific decision
    Then I can trace:
      ```sql
      SELECT
        intimation_id,
        numero_processo,
        partition_date,
        analyzed_at,
        analysis_method,
        confidence_breakdown.overall
      FROM read_parquet('s3://ia/decisions-*.parquet')
      WHERE numero_processo = '0000123-45.2024.8.22.0001'
      ORDER BY analyzed_at DESC
      ```
    And see: "Decision analyzed 3 times (original + 2 reanalyses)"
    And verify: "Current version analyzed on 2025-01-20 with v2.3.0"
    And ensure LGPD compliance with complete audit trail

  @time-travel @seasonality @temporal-patterns
  Scenario: Identify seasonal patterns in judicial outcomes
    Given I have 2+ years of historical decisions
    When I want to detect seasonal patterns
    Then I query:
      ```sql
      SELECT
        EXTRACT(MONTH FROM partition_date) AS month,
        EXTRACT(YEAR FROM partition_date) AS year,
        outcome,
        COUNT(*) AS decisions
      FROM read_parquet('s3://ia/decisions-*.parquet')
      WHERE sigla_tribunal = 'TJRO'
        AND partition_date >= '2023-01-01'
      GROUP BY month, year, outcome
      ORDER BY year, month
      ```
    And identify patterns:
      | finding | description |
      | December spike | 30% more decisions in December (end of year) |
      | July slowdown | 20% fewer decisions in July (winter break) |
      | Outcome shift | More "procedente" in Q4 vs Q1 |
    And predict: "Expect high volume in December 2025"

  @time-travel @lawyers @career-trajectory
  Scenario: Analyze lawyer career progression over years
    Given I have lawyer snapshots for 2023, 2024, 2025
    When I want to see how lawyer "5733" progressed
    Then I query career trajectory:
      ```sql
      SELECT
        EXTRACT(YEAR FROM partition_date) AS year,
        AVG(global_rating) AS avg_rating,
        AVG(total_cases) AS avg_cases,
        AVG(win_rate) AS avg_win_rate
      FROM read_parquet('s3://ia/lawyers-*.parquet')
      WHERE oab_number = '5733'
      GROUP BY year
      ORDER BY year
      ```
    And visualize progression:
      | year | rating | cases | win_rate |
      | 2023 | 1200 | 45 | 62% |
      | 2024 | 1420 | 89 | 68% |
      | 2025 | 1520 | 134 | 71% |
    And narrative: "Steady growth in rating and win rate over 3 years"

  @time-travel @anomaly @outlier-detection
  Scenario: Detect anomalies by comparing with historical baselines
    Given I have baseline statistics from 2024
    When I analyze 2025 data
    Then I compare:
      ```sql
      WITH baseline AS (
        SELECT
          AVG(confidence_breakdown.overall) AS avg_conf_2024,
          STDDEV(confidence_breakdown.overall) AS stddev_conf_2024
        FROM read_parquet('s3://ia/decisions-2024-*.parquet')
      ),
      current AS (
        SELECT
          partition_date,
          AVG(confidence_breakdown.overall) AS avg_conf
        FROM read_parquet('s3://ia/decisions-2025-*.parquet')
        GROUP BY partition_date
      )
      SELECT
        c.partition_date,
        c.avg_conf,
        b.avg_conf_2024,
        (c.avg_conf - b.avg_conf_2024) / b.stddev_conf_2024 AS z_score
      FROM current c, baseline b
      WHERE ABS((c.avg_conf - b.avg_conf_2024) / b.stddev_conf_2024) > 2
      ```
    And detect anomalies: "2025-01-18 confidence 3.2σ below baseline"
    And investigate: "System bug or data quality issue?"

  @time-travel @reporting @executive-dashboard
  Scenario: Build executive dashboard with time-series KPIs
    Given I need to report monthly KPIs to stakeholders
    When I query historical data:
      ```sql
      SELECT
        DATE_TRUNC('month', partition_date) AS month,
        COUNT(DISTINCT intimation_id) AS total_decisions,
        COUNT(DISTINCT numero_processo) AS unique_cases,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        SUM(CASE WHEN confidence_breakdown.overall > 0.80 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS high_confidence_pct,
        COUNT(DISTINCT winner_lawyer_oab) + COUNT(DISTINCT loser_lawyer_oab) AS unique_lawyers
      FROM read_parquet('s3://ia/decisions-*.parquet')
      WHERE partition_date >= '2024-01-01'
      GROUP BY month
      ORDER BY month
      ```
    Then I can visualize:
      | month | decisions | avg_confidence | high_conf_% | lawyers |
      | 2024-01 | 250000 | 0.72 | 45% | 12000 |
      | 2024-12 | 320000 | 0.81 | 68% | 15000 |
      | 2025-01 | 340000 | 0.85 | 75% | 16000 |
    And highlight: "Decisions +36%, Confidence +18%, Coverage +33%"
    And celebrate progress! 🎉
