Feature: Cross-Tribunal Analytics and Aggregations
  As a legal market analyst
  I want to run aggregated queries across all 27 Brazilian tribunals
  So that I can identify national trends, compare tribunal performance, and benchmark lawyers

  Background:
    Given Brazil has 27 state tribunals (TJs)
    And each tribunal exports daily parquet files
    And DuckDB can query multiple files with wildcards
    And pattern: causaganha-decisions-YYYY-MM-DD-*.parquet matches all tribunals

  @cross-tribunal @national-trends @outcomes
  Scenario: Analyze outcome distribution across all tribunals
    Given I have decisions from all 27 tribunals for January 2025
    When I run national aggregation query:
      ```sql
      SELECT
        outcome,
        COUNT(*) AS decisions,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY outcome
      ORDER BY decisions DESC
      ```
    Then I should see national outcome distribution:
      | outcome | decisions | percentage |
      | improcedente | 450000 | 45% |
      | procedente | 350000 | 35% |
      | parcialmente procedente | 180000 | 18% |
      | outros | 20000 | 2% |
    And I can compare with historical baselines
    And identify: "National improcedente rate increased 3% this month"

  @cross-tribunal @tribunal-comparison @performance
  Scenario: Compare average confidence scores across tribunals
    Given I want to identify which tribunals have highest analysis quality
    When I run cross-tribunal quality comparison:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS decisions,
        AVG(confidence_breakdown.overall) AS avg_confidence,
        AVG(confidence_breakdown.winner_identification) AS avg_winner_conf,
        AVG(confidence_breakdown.outcome_classification) AS avg_outcome_conf
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY avg_confidence DESC
      ```
    Then I should see tribunal quality rankings:
      | tribunal | decisions | avg_confidence | rank |
      | TJRO | 10000 | 0.85 | 1 (Best!) |
      | TJSP | 120000 | 0.82 | 2 |
      | TJRJ | 95000 | 0.81 | 3 |
      | ... | ... | ... | ... |
      | TJMG | 85000 | 0.62 | 27 (Needs attention) |
    And investigate: "Why is TJMG quality lower?"
    And possible causes: "Different text format, OCR quality, legal terminology"

  @cross-tribunal @volume @size-comparison
  Scenario: Compare decision volumes across tribunals
    Given different tribunals have different case loads
    When I query volume by tribunal:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS decisions,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage_of_national,
        RANK() OVER (ORDER BY COUNT(*) DESC) AS volume_rank
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY decisions DESC
      ```
    Then I should see:
      | tribunal | decisions | % of national | rank |
      | TJSP | 450000 | 35% | 1 (Largest) |
      | TJRJ | 280000 | 22% | 2 |
      | TJMG | 220000 | 17% | 3 |
      | ... | ... | ... | ... |
      | TJAC | 3000 | 0.2% | 27 (Smallest) |
    And calculate: "Top 3 tribunals represent 74% of national volume"

  @cross-tribunal @lawyers @national-rankings
  Scenario: Build national lawyer rankings across all tribunals
    Given I have lawyer data from all states
    And some lawyers operate in multiple tribunals
    When I calculate national rankings:
      ```sql
      WITH lawyer_stats AS (
        SELECT
          winner_lawyer_oab,
          winner_lawyer_state,
          COUNT(*) AS cases,
          SUM(CASE WHEN outcome = 'procedente' THEN 1 ELSE 0 END) AS wins,
          SUM(CASE WHEN outcome = 'procedente' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS win_rate,
          COUNT(DISTINCT sigla_tribunal) AS tribunals_active
        FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
        WHERE winner_lawyer_oab IS NOT NULL
        GROUP BY winner_lawyer_oab, winner_lawyer_state
        HAVING COUNT(*) >= 10  -- Minimum 10 cases
      )
      SELECT
        winner_lawyer_oab,
        cases,
        win_rate,
        tribunals_active,
        RANK() OVER (ORDER BY win_rate DESC, cases DESC) AS national_rank
      FROM lawyer_stats
      ORDER BY national_rank
      LIMIT 100
      ```
    Then I can publish: "Top 100 Lawyers in Brazil by Win Rate"
    And highlight multi-tribunal lawyers: "OAB 5733 active in 5 tribunals"

  @cross-tribunal @speed @processing-time
  Scenario: Compare analysis processing time across tribunals
    Given different tribunals may have different decision formats
    When I measure analysis performance:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS decisions,
        AVG(EXTRACT(EPOCH FROM (analyzed_at - data_disponibilizacao))) AS avg_analysis_time_seconds,
        AVG(EXTRACT(EPOCH FROM (analyzed_at - data_disponibilizacao))) / 60 AS avg_analysis_time_minutes
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      WHERE analyzed_at IS NOT NULL
      GROUP BY sigla_tribunal
      ORDER BY avg_analysis_time_seconds
      ```
    Then I can identify:
      | tribunal | avg_time | status |
      | TJRO | 2.5 min | Fast ✅ |
      | TJSP | 3.1 min | Normal ✅ |
      | TJMG | 8.2 min | Slow ⚠️ |
    And investigate: "Why is TJMG 3x slower?"
    And optimize processing for slow tribunals

  @cross-tribunal @outcomes @regional-patterns
  Scenario: Identify regional patterns in judicial outcomes
    Given Brazil has 5 regions: North, Northeast, Central-West, Southeast, South
    When I map tribunals to regions and aggregate:
      ```sql
      WITH regional_mapping AS (
        SELECT sigla_tribunal,
          CASE
            WHEN sigla_tribunal IN ('TJAC', 'TJAP', 'TJAM', 'TJPA', 'TJRO', 'TJRR', 'TJTO') THEN 'North'
            WHEN sigla_tribunal IN ('TJAL', 'TJBA', 'TJCE', 'TJMA', 'TJPB', 'TJPE', 'TJPI', 'TJRN', 'TJSE') THEN 'Northeast'
            WHEN sigla_tribunal IN ('TJDF', 'TJGO', 'TJMT', 'TJMS') THEN 'Central-West'
            WHEN sigla_tribunal IN ('TJES', 'TJMG', 'TJRJ', 'TJSP') THEN 'Southeast'
            WHEN sigla_tribunal IN ('TJPR', 'TJSC', 'TJRS') THEN 'South'
          END AS region
        FROM (SELECT DISTINCT sigla_tribunal FROM read_parquet('s3://ia/decisions-2025-01-*.parquet'))
      )
      SELECT
        r.region,
        d.outcome,
        COUNT(*) AS decisions,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY r.region) AS pct_in_region
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet') d
      JOIN regional_mapping r ON d.sigla_tribunal = r.sigla_tribunal
      GROUP BY r.region, d.outcome
      ORDER BY r.region, decisions DESC
      ```
    Then I can compare regional patterns:
      | region | procedente_% | improcedente_% | notes |
      | Southeast | 38% | 47% | More plaintiff-friendly |
      | South | 32% | 51% | More defendant-friendly |
      | Northeast | 35% | 45% | National average |
    And publish report: "Regional Differences in Judicial Outcomes"

  @cross-tribunal @judge-extraction @difficulty
  Scenario: Identify which tribunals have hardest judge extraction
    Given judge extraction confidence varies by tribunal
    When I measure judge extraction difficulty:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS decisions,
        AVG(confidence_breakdown.judge_extraction) AS avg_judge_conf,
        SUM(CASE WHEN judge_name IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS missing_judge_pct
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY avg_judge_conf
      ```
    Then I can prioritize improvements:
      | tribunal | avg_judge_conf | missing_% | action |
      | TJRO | 0.92 | 2% | Good ✅ |
      | TJSP | 0.85 | 8% | Acceptable ✅ |
      | TJMG | 0.58 | 35% | Needs pattern updates ⚠️ |
    And focus engineering effort: "Improve judge extraction for TJMG"

  @cross-tribunal @embeddings @consistency
  Scenario: Validate embedding quality across all tribunals
    Given embeddings are generated for all tribunals
    When I check embedding quality metrics:
      ```sql
      SELECT
        SUBSTRING(filename, -13, 4) AS tribunal,
        COUNT(*) AS embeddings,
        AVG(list_length(texto_embedding)) AS avg_dimension,
        AVG(list_sum(list_transform(texto_embedding, x -> x * x))) AS avg_l2_norm_squared,
        SUM(CASE WHEN texto_embedding IS NULL THEN 1 ELSE 0 END) AS null_embeddings
      FROM read_parquet('s3://ia/embeddings-2025-01-*.parquet', filename=true)
      GROUP BY tribunal
      ORDER BY tribunal
      ```
    Then all tribunals should have:
      | check | expected |
      | avg_dimension | 1024 |
      | avg_l2_norm_squared | ≈ 1.0 |
      | null_embeddings | 0 |
    And flag anomalies: "TJMG has 150 null embeddings!"
    And remediate: causaganha embeddings regenerate --tribunal TJMG --date 2025-01-15

  @cross-tribunal @cost @tribunal-cost-breakdown
  Scenario: Calculate analysis costs per tribunal
    Given different tribunals have different volumes
    When I calculate per-tribunal costs:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS decisions,
        COUNT(*) * 0.00008 AS embedding_cost_usd,
        COUNT(*) * 0.0001 AS llm_analysis_cost_usd,
        (COUNT(*) * 0.00008 + COUNT(*) * 0.0001) AS total_cost_usd,
        (COUNT(*) * 0.00008 + COUNT(*) * 0.0001) * 100.0 / SUM(COUNT(*) * 0.00008 + COUNT(*) * 0.0001) OVER () AS pct_of_total_cost
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY total_cost_usd DESC
      ```
    Then I can budget by tribunal:
      | tribunal | decisions | total_cost | % of budget |
      | TJSP | 450000 | $81 | 35% |
      | TJRJ | 280000 | $50 | 22% |
      | TJAC | 3000 | $0.54 | 0.2% |
    And justify costs: "TJSP represents 35% of decisions and 35% of costs (fair)"

  @cross-tribunal @winner-loser @symmetry
  Scenario: Analyze winner/loser identification symmetry across tribunals
    Given winner and loser should be identified with similar confidence
    When I check symmetry:
      ```sql
      SELECT
        sigla_tribunal,
        AVG(confidence_breakdown.winner_identification) AS avg_winner_conf,
        AVG(confidence_breakdown.loser_identification) AS avg_loser_conf,
        AVG(confidence_breakdown.winner_identification) - AVG(confidence_breakdown.loser_identification) AS asymmetry
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY ABS(asymmetry) DESC
      ```
    Then I can detect asymmetries:
      | tribunal | winner_conf | loser_conf | asymmetry | issue |
      | TJRO | 0.88 | 0.86 | +0.02 | Balanced ✅ |
      | TJSP | 0.85 | 0.83 | +0.02 | Balanced ✅ |
      | TJMG | 0.72 | 0.58 | +0.14 | Loser extraction weaker! ⚠️ |
    And investigate: "Why is loser extraction harder in TJMG?"

  @cross-tribunal @storage @parquet-size-analysis
  Scenario: Analyze parquet file sizes across tribunals
    Given file size correlates with decision volume and complexity
    When I query parquet metadata:
      ```sql
      SELECT
        filename,
        SUBSTRING(filename, -13, 4) AS tribunal,
        file_size / 1024 / 1024 AS size_mb,
        row_count,
        (file_size / row_count) AS bytes_per_decision
      FROM parquet_metadata('s3://ia/decisions-2025-01-*.parquet')
      ORDER BY size_mb DESC
      ```
    Then I can optimize storage:
      | tribunal | size_mb | decisions | bytes_per_decision | notes |
      | TJSP | 180 MB | 450000 | 400 | Normal |
      | TJRO | 42 MB | 10000 | 4200 | Large decisions! |
      | TJAC | 1.2 MB | 3000 | 400 | Normal |
    And investigate: "Why are TJRO decisions 10x larger?"
    And optimize compression if needed

  @cross-tribunal @tribunal-specialization @case-types
  Scenario: Identify tribunal specializations by decision type
    Given some tribunals may specialize in certain case types
    When I analyze decision type distribution:
      ```sql
      SELECT
        sigla_tribunal,
        decision_type,
        COUNT(*) AS decisions,
        COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY sigla_tribunal) AS pct_in_tribunal
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      WHERE decision_type IS NOT NULL
      GROUP BY sigla_tribunal, decision_type
      ORDER BY sigla_tribunal, decisions DESC
      ```
    Then I can identify specializations:
      | tribunal | top_decision_type | % | insight |
      | TJSP | Apelação Cível | 65% | Civil focus |
      | TJRO | Apelação Criminal | 45% | Balanced |
      | TJDF | Mandado de Segurança | 38% | Administrative focus |
    And understand: "Each tribunal has different case mix"

  @cross-tribunal @data-quality @completeness
  Scenario: Measure data completeness across tribunals
    Given some fields may be missing in certain tribunals
    When I check field completeness:
      ```sql
      SELECT
        sigla_tribunal,
        COUNT(*) AS total_decisions,
        SUM(CASE WHEN winner_lawyer_oab IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS winner_oab_pct,
        SUM(CASE WHEN loser_lawyer_oab IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS loser_oab_pct,
        SUM(CASE WHEN judge_name IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS judge_pct,
        SUM(CASE WHEN decision_type IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS decision_type_pct
      FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      GROUP BY sigla_tribunal
      ORDER BY winner_oab_pct DESC
      ```
    Then I can create data quality scorecard:
      | tribunal | winner_oab | loser_oab | judge | decision_type | score |
      | TJRO | 95% | 92% | 98% | 88% | A+ |
      | TJSP | 88% | 85% | 92% | 82% | A |
      | TJMG | 65% | 58% | 62% | 55% | C (Needs work) |
    And prioritize improvements for low-scoring tribunals

  @cross-tribunal @benchmark @national-averages
  Scenario: Calculate national benchmarks for lawyer performance
    Given I want to benchmark lawyers against national averages
    When I calculate national statistics:
      ```sql
      WITH national_stats AS (
        SELECT
          AVG(CASE WHEN outcome = 'procedente' THEN 1.0 ELSE 0.0 END) AS national_win_rate,
          STDDEV(CASE WHEN outcome = 'procedente' THEN 1.0 ELSE 0.0 END) AS win_rate_stddev
        FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
      ),
      lawyer_performance AS (
        SELECT
          winner_lawyer_oab,
          COUNT(*) AS cases,
          AVG(CASE WHEN outcome = 'procedente' THEN 1.0 ELSE 0.0 END) AS lawyer_win_rate
        FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
        WHERE winner_lawyer_oab IS NOT NULL
        GROUP BY winner_lawyer_oab
        HAVING COUNT(*) >= 30
      )
      SELECT
        l.winner_lawyer_oab,
        l.cases,
        l.lawyer_win_rate,
        n.national_win_rate,
        (l.lawyer_win_rate - n.national_win_rate) / n.win_rate_stddev AS z_score
      FROM lawyer_performance l, national_stats n
      WHERE ABS((l.lawyer_win_rate - n.national_win_rate) / n.win_rate_stddev) > 2
      ORDER BY z_score DESC
      ```
    Then I can identify outlier lawyers:
      | oab | win_rate | national_avg | z_score | classification |
      | 5733 | 78% | 35% | +4.2σ | Elite (Top 0.01%) |
      | 8921 | 72% | 35% | +3.5σ | Excellent (Top 0.1%) |
      | 1234 | 12% | 35% | -2.8σ | Below average |

  @cross-tribunal @export @consolidated-report
  Scenario: Export consolidated cross-tribunal report to local parquet
    Given I ran complex cross-tribunal analytics
    When I want to share results with stakeholders
    Then I export to local parquet:
      ```sql
      COPY (
        SELECT
          sigla_tribunal,
          COUNT(*) AS decisions,
          AVG(confidence_breakdown.overall) AS avg_confidence,
          COUNT(DISTINCT winner_lawyer_oab) AS unique_lawyers,
          AVG(CASE WHEN outcome = 'procedente' THEN 1.0 ELSE 0.0 END) AS procedente_rate
        FROM read_parquet('s3://ia/decisions-2025-01-*.parquet')
        GROUP BY sigla_tribunal
      ) TO 'cross_tribunal_summary_2025_01.parquet'
      ```
    And share file with team
    And import into BI tools (Power BI, Tableau, Metabase)
    And build executive dashboards
