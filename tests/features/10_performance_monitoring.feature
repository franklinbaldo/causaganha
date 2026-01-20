Feature: Performance and System Monitoring
  As a system administrator
  I want to monitor system performance and resource usage
  So that I can ensure reliable and efficient operations

  Background:
    Given the CausaGanha system is running
    And monitoring is enabled

  # ============================================================================
  # PIPELINE PERFORMANCE
  # ============================================================================

  Scenario: Track pipeline execution time
    Given there are 100 intimations to process
    When I run the complete pipeline
    Then the total execution time should be recorded
    And execution time per stage should be recorded
    And the timing data should be logged

  Scenario: Measure throughput for each stage
    Given the pipeline processes 500 intimations
    When the pipeline completes
    Then collection throughput should be calculated (intimations/second)
    And archival throughput should be calculated (PDFs/second)
    And analysis throughput should be calculated (analyses/second)
    And scoring throughput should be calculated (ratings/second)
    And throughput metrics should be logged

  Scenario: Identify performance bottlenecks
    Given the pipeline has completed
    When I analyze performance metrics
    Then the slowest stage should be identified
    And the stage execution times should be compared
    And bottleneck recommendations should be provided

  Scenario: Track performance trends over time
    Given the pipeline has run daily for 30 days
    When I view performance trends
    Then execution times should be plotted over time
    And throughput should be plotted over time
    And performance degradation should be detected
    And alerts should be raised for significant slowdowns

  # ============================================================================
  # API PERFORMANCE
  # ============================================================================

  Scenario: Monitor PJe API response times
    Given the collect command is running
    When API requests are made
    Then response times should be measured for each request
    And average response time should be calculated
    And slow requests (> 5 seconds) should be logged
    And API performance should be tracked per tribunal

  Scenario: Track API error rates
    Given 1000 API requests are made
    When some requests fail
    Then the error rate should be calculated (errors/total requests)
    And errors should be categorized by type
    And tribunals with high error rates should be identified
    And alerts should be raised for error rates > 5%

  Scenario: Monitor LLM API performance
    Given the analyze command processes 100 decisions
    When LLM requests are made
    Then LLM response times should be measured
    And average response time should be calculated
    And slow responses (> 30 seconds) should be logged
    And LLM token usage should be tracked

  Scenario: Track LLM cost metrics
    Given the analyze command runs for a day
    When LLM requests are completed
    Then total tokens used should be calculated
    And estimated cost should be calculated
    And cost per analysis should be calculated
    And cost trends should be tracked

  # ============================================================================
  # DATABASE PERFORMANCE
  # ============================================================================

  Scenario: Monitor database query performance
    Given the pipeline is running
    When database queries are executed
    Then query execution times should be measured
    And slow queries (> 100ms) should be logged
    And query performance should be analyzed

  Scenario: Track database connection pool usage
    Given the system is processing data
    When database connections are used
    Then active connections should be counted
    And connection pool utilization should be calculated
    And connection pool exhaustion should be detected
    And alerts should be raised for high utilization

  Scenario: Monitor database storage growth
    Given the system has been running for 30 days
    When I check database metrics
    Then total database size should be recorded
    And daily growth rate should be calculated
    And storage projections should be provided
    And alerts should be raised if storage is low

  Scenario: Identify expensive database operations
    When I analyze database performance
    Then the most expensive queries should be identified
    And table scan operations should be detected
    And missing index recommendations should be provided
    And optimization suggestions should be given

  # ============================================================================
  # RESOURCE UTILIZATION
  # ============================================================================

  Scenario: Monitor CPU usage during pipeline execution
    Given the pipeline is running
    When CPU usage is measured
    Then CPU utilization should be recorded every 10 seconds
    And peak CPU usage should be identified
    And CPU usage should be correlated with pipeline stages
    And alerts should be raised for sustained high CPU (> 90%)

  Scenario: Monitor memory usage
    Given the pipeline processes large batches
    When memory usage is measured
    Then current memory usage should be recorded
    And peak memory usage should be identified
    And memory leaks should be detected
    And alerts should be raised for high memory usage

  Scenario: Monitor disk I/O performance
    Given PDFs are being downloaded and processed
    When disk operations occur
    Then read/write throughput should be measured
    And I/O wait times should be recorded
    And disk bottlenecks should be identified

  Scenario: Track network bandwidth usage
    Given the pipeline is collecting from multiple tribunals
    When network requests are made
    Then bandwidth usage should be measured
    And peak bandwidth should be identified
    And bandwidth limits should be respected

  # ============================================================================
  # CONCURRENT PROCESSING METRICS
  # ============================================================================

  Scenario: Monitor concurrent processing efficiency
    Given 100 intimations are processed with concurrency=10
    When the processing completes
    Then concurrency utilization should be calculated
    And idle time should be measured
    And concurrency recommendations should be provided

  Scenario: Track thread pool usage
    Given concurrent operations are running
    When threads are allocated
    Then active threads should be counted
    And thread pool utilization should be calculated
    And thread starvation should be detected

  # ============================================================================
  # SYSTEM HEALTH CHECKS
  # ============================================================================

  Scenario: Perform health check on all services
    When I run the health check command
    Then database connectivity should be verified
    And PJe API accessibility should be verified
    And Gemini LLM API accessibility should be verified
    And Internet Archive API accessibility should be verified
    And disk space should be verified
    And a health status should be reported

  Scenario: Detect service degradation
    Given the system has been running normally
    When a service starts responding slowly
    Then the degradation should be detected
    And the affected service should be identified
    And an alert should be raised
    And degradation metrics should be logged

  Scenario: Monitor uptime and availability
    When I check system uptime
    Then total uptime should be calculated
    And downtime incidents should be listed
    And availability percentage should be calculated
    And SLA compliance should be reported

  # ============================================================================
  # BATCH PROCESSING METRICS
  # ============================================================================

  Scenario: Track batch processing efficiency
    Given batches of 50 intimations are processed
    When processing completes
    Then batch processing time should be recorded
    And items per batch should be verified
    And batch efficiency (actual vs expected time) should be calculated

  Scenario: Optimize batch sizes based on performance
    Given different batch sizes are tested (10, 50, 100, 200)
    When performance is measured for each size
    Then optimal batch size should be identified
    And recommendations should be provided
    And batch size should be tuned automatically

  # ============================================================================
  # ERROR RATE MONITORING
  # ============================================================================

  Scenario: Track error rates per pipeline stage
    Given the pipeline processes 1000 intimations
    When errors occur in different stages
    Then error rate should be calculated for collect stage
    And error rate should be calculated for archive stage
    And error rate should be calculated for analyze stage
    And error rate should be calculated for score stage
    And stages with high error rates should be flagged

  Scenario: Alert on elevated error rates
    Given normal error rate is 2%
    And current error rate is 15%
    When the error rate is checked
    Then an alert should be raised
    And the error spike should be investigated
    And error details should be provided

  # ============================================================================
  # CACHE PERFORMANCE
  # ============================================================================

  Scenario: Monitor cache hit rates
    Given caching is enabled for embeddings
    When embeddings are requested
    Then cache hits should be counted
    And cache misses should be counted
    And hit rate should be calculated
    And cache effectiveness should be evaluated

  Scenario: Track cache memory usage
    Given the cache stores embeddings
    When cache usage is measured
    Then cache size should be recorded
    And cache item count should be recorded
    And eviction rate should be calculated
    And cache configuration should be optimized

  # ============================================================================
  # SCHEDULED JOB MONITORING
  # ============================================================================

  Scenario: Track scheduled job execution
    Given the pipeline is scheduled to run daily at 2 AM
    When the job executes
    Then execution start time should be recorded
    And execution end time should be recorded
    And execution duration should be calculated
    And success/failure should be recorded

  Scenario: Alert on missed scheduled executions
    Given the pipeline is scheduled daily
    And the last execution was 48 hours ago
    When the schedule is checked
    Then a missed execution should be detected
    And an alert should be raised
    And the reason for the miss should be investigated

  Scenario: Track scheduled job success rate
    Given the pipeline has run 30 times in 30 days
    And 28 runs succeeded, 2 failed
    When I check job reliability
    Then success rate should be calculated (93.3%)
    And failed runs should be listed
    And failure patterns should be identified

  # ============================================================================
  # RATE LIMITING METRICS
  # ============================================================================

  Scenario: Monitor API rate limit usage
    Given PJe API has rate limits of 100 requests/minute
    When requests are made
    Then request count should be tracked per minute
    And rate limit utilization should be calculated
    And alerts should be raised approaching limits (> 80%)

  Scenario: Track rate limit throttling events
    Given rate limits are enforced
    When throttling occurs
    Then throttling events should be counted
    And wait times should be recorded
    And impact on throughput should be calculated

  # ============================================================================
  # LOGGING METRICS
  # ============================================================================

  Scenario: Monitor logging volume
    Given the system generates structured logs
    When logs are written
    Then log volume should be measured (MB/hour)
    And log growth rate should be tracked
    And excessive logging should be detected

  Scenario: Track log levels distribution
    When I analyze log output
    Then logs should be counted by level (DEBUG, INFO, WARNING, ERROR)
    And the distribution should be analyzed
    And unusual patterns should be detected (e.g., too many ERRORs)

  # ============================================================================
  # ALERTING & NOTIFICATIONS
  # ============================================================================

  Scenario: Configure performance alert thresholds
    Given monitoring is configured
    When I set alert thresholds:
      | Metric              | Threshold |
      | Pipeline duration   | > 60 min  |
      | Error rate          | > 5%      |
      | CPU usage           | > 90%     |
      | Memory usage        | > 85%     |
      | Disk space          | < 10%     |
    Then alerts should trigger when thresholds are exceeded

  Scenario: Send alerts to configured channels
    Given alerts are configured
    And an alert condition is met
    When the alert is triggered
    Then notification should be sent to email
    And notification should be sent to Slack (if configured)
    And the alert should be logged

  # ============================================================================
  # PERFORMANCE REPORTING
  # ============================================================================

  Scenario: Generate daily performance report
    When the daily report is generated
    Then the report should include pipeline statistics
    And the report should include resource utilization
    And the report should include error rates
    And the report should include API performance
    And the report should highlight anomalies

  Scenario: Compare performance across time periods
    Given I want to compare this week vs last week
    When I generate a comparison report
    Then execution times should be compared
    And throughput should be compared
    And error rates should be compared
    And improvements or degradations should be highlighted

  # ============================================================================
  # CAPACITY PLANNING
  # ============================================================================

  Scenario: Predict resource needs based on trends
    Given 90 days of performance data
    When I run capacity planning analysis
    Then future resource needs should be projected
    And storage growth should be forecasted
    And processing capacity should be estimated
    And scaling recommendations should be provided

  Scenario: Identify scaling thresholds
    Given current system capacity is measured
    When load increases
    Then breaking points should be identified
    And scaling triggers should be defined
    And proactive scaling recommendations should be made

  # ============================================================================
  # OBSERVABILITY DASHBOARD
  # ============================================================================

  Scenario: Real-time monitoring dashboard
    Given the monitoring dashboard is accessible
    When I view the dashboard
    Then current pipeline status should be displayed
    And real-time metrics should be shown
    And recent errors should be listed
    And system health should be indicated
    And alerts should be highlighted

  Scenario: Historical metrics visualization
    Given historical data is available
    When I view metric charts
    Then execution times should be plotted over time
    And throughput should be graphed
    And error rates should be charted
    And resource usage should be visualized
    And trends should be identifiable

  # ============================================================================
  # PERFORMANCE OPTIMIZATION
  # ============================================================================

  Scenario: Identify optimization opportunities
    When I analyze system performance
    Then slow operations should be identified
    And inefficient queries should be listed
    And suboptimal configurations should be detected
    And optimization recommendations should be provided

  Scenario: Measure impact of optimizations
    Given an optimization is implemented
    When before/after metrics are compared
    Then performance improvement should be quantified
    And ROI of optimization should be calculated
    And success should be validated
