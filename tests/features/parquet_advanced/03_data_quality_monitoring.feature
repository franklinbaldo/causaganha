Feature: Automated Data Quality Monitoring
  As a platform operator
  I want automated quality checks on exported parquet files
  So that I can detect and fix issues before they impact users

  Background:
    Given parquet files are exported daily to Internet Archive
    And quality checks run automatically after export
    And alerts are sent for quality degradation

  @quality @validation @daily-checks
  Scenario: Daily automated quality checks after export
    Given yesterday's parquet files were exported
    When the daily quality check job runs
    Then it should validate:
      | check | description | threshold |
      | Row count match | Decisions == Embeddings rows | 100% match |
      | No null embeddings | All embeddings non-null | 0 nulls |
      | Hash validation | texto_hash matches texto | 100% match |
      | Confidence range | All confidence scores 0.0-1.0 | 100% valid |
      | Average confidence | Overall confidence | > 0.70 |
      | Missing analyses | Decisions without analysis | < 1% |
      | Duplicate intimation_ids | No duplicates | 0 duplicates |
      | File size reasonable | Not too small/large | 10-200 MB |
    And generate quality report with pass/fail status
    And alert if any check fails

  @quality @validation @schema-validation
  Scenario: Validate parquet schema matches expected
    Given I export parquet files with schema v2
    When I run schema validation
    Then decisions parquet should have columns:
      | required_columns |
      | intimation_id (int64) |
      | numero_processo (string) |
      | texto (string) |
      | texto_sections (struct) |
      | confidence_breakdown (struct) |
      | outcome (string) |
    And embeddings parquet should have columns:
      | required_columns |
      | intimation_id (int64) |
      | texto_embedding (list<float32>[1024]) |
      | embedding_model (string) |
      | texto_hash (string) |
    And alert if schema mismatch detected

  @quality @validation @confidence-degradation
  Scenario: Detect confidence degradation over time
    Given I track daily average confidence
    And last week's average was 0.82
    When today's average is 0.68 (17% drop)
    Then the system should:
      | action |
      | Alert: "Confidence dropped 17% from 0.82 to 0.68" |
      | Include breakdown by component (winner_id, outcome, etc.) |
      | Compare with same day last week |
      | Suggest possible causes (model change, data quality) |
      | Create incident ticket automatically |
    And I should investigate root cause

  @quality @validation @missing-data-detection
  Scenario: Detect missing or corrupted parquet files
    Given expected files for 2025-01-20:
      | file_type | expected_count |
      | decisions | 27 (one per tribunal) |
      | embeddings | 27 |
      | lawyers | 1 (shared) |
      | partes | 27 |
    When I check Internet Archive
    And only 25 decision files exist (TJMG and TJSP missing)
    Then the system should:
      | action |
      | Alert: "Missing parquet files for 2025-01-20" |
      | List missing files: decisions-2025-01-20-TJMG.parquet, decisions-2025-01-20-TJSP.parquet |
      | Check if export failed or upload failed |
      | Attempt re-export for missing tribunals |
      | Track in parquet_exports table as "missing" |

  @quality @validation @data-consistency
  Scenario: Validate consistency between related parquet files
    Given I have decisions and embeddings for 2025-01-20 TJRO
    When I run consistency checks
    Then I should verify:
      | consistency_check | validation |
      | Row count match | len(decisions) == len(embeddings) |
      | Key alignment | All decisions.intimation_id in embeddings.intimation_id |
      | No orphans | No embeddings without matching decision |
      | Hash match | texto SHA256 == embeddings.texto_hash |
      | Date consistency | All partition_date == 2025-01-20 |
      | Tribunal consistency | All sigla_tribunal == 'TJRO' |
    And all checks should pass
    And alert if any inconsistency found

  @quality @validation @outcome-distribution
  Scenario: Monitor outcome distribution for anomalies
    Given historical outcome distribution:
      | outcome | typical_percentage |
      | procedente | 35% |
      | improcedente | 45% |
      | parcialmente procedente | 18% |
      | others | 2% |
    When today's distribution is:
      | outcome | today_percentage |
      | procedente | 5% (should be 35%) |
      | improcedente | 92% (should be 45%) |
      | parcialmente procedente | 2% (should be 18%) |
      | others | 1% |
    Then the system should:
      | action |
      | Alert: "Outcome distribution anomaly detected" |
      | Show: "procedente dropped from 35% to 5% (-86%)" |
      | Show: "improcedente increased from 45% to 92% (+104%)" |
      | Suggest: "Possible model bug or data issue" |
      | Recommend: "Review sample decisions manually" |

  @quality @validation @embedding-quality
  Scenario: Validate embedding vector quality
    Given I generate embeddings for 10000 decisions
    When I run embedding quality checks
    Then I should validate:
      | check | validation | threshold |
      | Dimension | All vectors have 1024 dimensions | 100% |
      | Normalization | L2 norm ≈ 1.0 | > 99% within 0.9-1.1 |
      | No zeros | No all-zero vectors | 0 zero vectors |
      | No NaN/Inf | No invalid floats | 0 invalid |
      | Similarity sanity | Similar texts have high cosine sim | > 0.7 for duplicates |
    And alert if embedding generation failed

  @quality @validation @cost-monitoring
  Scenario: Monitor and alert on cost anomalies
    Given typical daily export cost is $50
    When today's cost is $500 (10x increase)
    Then the system should:
      | action |
      | Alert: "Export cost 10x higher than usual" |
      | Break down: "$450 embeddings, $30 sections, $20 analysis" |
      | Investigate: "Why 10x more decisions processed?" |
      | Check: "Did we re-export historical data accidentally?" |
      | Prevent: "Pause further exports until reviewed" |
    And I should approve before continuing

  @quality @validation @performance-degradation
  Scenario: Detect export performance degradation
    Given typical export time is 2 hours per day
    When today's export took 8 hours (4x slower)
    Then the system should:
      | action |
      | Alert: "Export time 4x slower than usual" |
      | Profile: Which step is slow (embedding? section extraction? upload?) |
      | Check: "Is Internet Archive slow today?" |
      | Check: "Did tribunal data volume increase?" |
      | Suggest: "Scale up workers or optimize pipeline" |

  @quality @validation @tribunal-comparison
  Scenario: Compare quality metrics across tribunals
    Given I have exports for all 27 tribunals
    When I generate cross-tribunal quality report
    Then I should see:
      | tribunal | avg_confidence | missing_analysis_pct | avg_file_size_mb |
      | TJRO | 0.85 | 0.5% | 45 MB |
      | TJSP | 0.78 | 1.2% | 120 MB |
      | TJRJ | 0.82 | 0.8% | 95 MB |
      | TJMG | 0.62 ⚠️ | 5.3% ⚠️ | 35 MB |
    And identify outliers (TJMG has unusually low quality)
    And investigate: "Why is TJMG quality worse?"

  @quality @validation @historical-tracking
  Scenario: Track quality metrics over time
    Given I track quality metrics daily for 90 days
    When I generate quality trend report
    Then I should visualize:
      | metric | trend |
      | Average confidence | Increasing from 0.68 to 0.82 (improvement!) |
      | Missing analyses | Decreasing from 3% to 0.5% (improvement!) |
      | Embedding errors | Stable at 0% (good!) |
      | Section extraction quality | Increasing from 65% to 82% |
    And identify: "Quality improved after model update on day 45"
    And celebrate: "We're getting better!" 🎉

  @quality @validation @automated-remediation
  Scenario: Automatically fix common quality issues
    Given I detect quality issue: "15% of embeddings are null"
    When automatic remediation is enabled
    Then the system should:
      | step | action |
      | 1 | Identify affected intimation_ids |
      | 2 | Regenerate embeddings for those IDs |
      | 3 | Update embeddings parquet with fixed embeddings |
      | 4 | Re-upload to Internet Archive |
      | 5 | Re-run quality checks to verify fix |
      | 6 | Log remediation action and success |
    And quality issue should be resolved automatically
    And human should be notified of auto-fix

  @quality @validation @sampling-validation
  Scenario: Validate quality using random sampling
    Given I exported 100000 decisions
    And full validation would be expensive
    When I run sampled validation on 1000 random decisions (1%)
    Then I should:
      | check | sample_size |
      | Download 1000 random decisions | 1% sample |
      | Validate texto_hash matches texto | 1000 |
      | Validate confidence ranges | 1000 |
      | Manually review 10 random decisions | 0.01% sample |
    And extrapolate: "If 1% sample is 98% quality, full dataset likely 98% ± 2%"
    And flag for full validation if sample quality < 95%

  @quality @validation @regression-testing
  Scenario: Regression test after code changes
    Given I deployed new analysis code version 2.3.0
    When I export today's decisions
    Then I should compare with yesterday (version 2.2.9):
      | metric | v2.2.9 | v2.3.0 | change |
      | Avg confidence | 0.82 | 0.84 | +2.4% ✅ |
      | Missing judge | 12% | 8% | -33% ✅ |
      | Processing time | 120 min | 90 min | -25% ✅ |
      | Cost per decision | $0.0012 | $0.0010 | -17% ✅ |
    And verify no regressions (all metrics improved or stable)
    And approve deployment if quality maintained/improved

  @quality @validation @alert-configuration
  Scenario: Configure quality alert thresholds
    Given I want to customize alert sensitivity
    When I configure thresholds:
      ```yaml
      quality_alerts:
        confidence_drop:
          threshold: 10%  # Alert if confidence drops > 10%
          severity: warning
        missing_analyses:
          threshold: 2%  # Alert if > 2% missing
          severity: error
        cost_increase:
          threshold: 50%  # Alert if cost > 50% higher
          severity: warning
        file_missing:
          threshold: 1  # Alert if any file missing
          severity: critical
      ```
    Then alerts should respect configured thresholds
    And I can tune sensitivity based on importance
