# Launch Plan (Testing, Rollout, Communication)

This section outlines how to test and roll out the revamped CausaGanha system, from a development alpha to a production-ready release. It covers internal testing, staged rollout of v2, and how we’ll communicate changes to stakeholders.

## Testing & Validation

Before any public launch, the team will conduct thorough testing of the v2 system with real data:

*   **Integration Testing (Pre-Launch):** Run end-to-end tests using a sample of real court data. For example, collect one day’s worth of TJRO cases, run through archive → analyze → score, and then manually verify the results against the known outcomes from v1 or ground truth. The goal is to ensure that v2’s analytics (lawyer win/lose identification and ratings) match expectations and that no data is lost in the new pipeline. Key metrics to validate include: number of cases processed vs. expected, accuracy of AI-extracted winners, and integrity of the DuckDB (e.g., no missing fields).
*   **Performance Benchmarking:** Simulate a larger load (e.g., a full month of data) on the staging environment to ensure the system can handle it within time and resource limits. This helps tune batch sizes or parallelism before going live.
*   **Regression Comparison with v1:** For a period, run v1 and v2 in parallel on the same input and compare outputs. This parallel run (shadow testing) will highlight any discrepancies. For instance, if v2’s LLM misclassifies a case outcome that v1’s method handled, we’ll investigate and fix the prompt or logic. This ensures that v2 is truly an improvement or at least consistent with v1 on existing capabilities.
*   **User Acceptance Testing:** Although end-users are not directly interacting with the pipeline (they consume outputs), we may share preliminary v2 results with a small group of friendly users (researchers, etc.) to gather feedback. They might check if the rankings “make sense” or if any obvious errors appear in the published data.

All testing phases above should be completed by “Week 4” of the timeline, yielding confidence that v2 is ready to take over.

## Rollout Strategy

The rollout to production will be gradual to mitigate risk. The plan:

1.  **Soft Launch (Parallel Run):** In the first week of launch (e.g., Week 5), deploy the v2 system alongside the v1 system. Both will ingest daily data: v1 will continue its normal operation (scraping, etc.), and v2 will use the API pipeline, but v2’s results won’t yet be published or relied upon. This shadow period allows monitoring of v2 in a production-like setting without jeopardizing data quality. Daily comparisons will be made between v1 and v2 outputs.
2.  **Primary Switchover:** In the second week (Week 6), if all looks good, designate v2 as the primary system. This means the data published on the Internet Archive and any new analytics will come from v2. v1 will be kept running in the background for a short safety period – e.g., we’ll still collect data via v1 but not use it, just in case v2 encounters an unexpected issue, we have v1 as a fall-back.
3.  **Rollback Plan:** Should any critical issue arise during or after the switchover (for instance, v2 misses a large portion of data or produces incorrect rankings), we are prepared to revert. The v1 system (scraper and old pipeline) will be retained for at least a month. In a rollback scenario, we would re-run v1 on any missed data and republish the v1 outputs to IA to correct the record, then fix v2 before attempting rollout again. Clear versioning (e.g., tagging releases) will ensure we know which version is producing data at any time, aiding a rollback if needed.
4.  **Monitoring During Rollout:** During the parallel run and initial switchover, we will closely monitor logs, run health checks, and possibly implement a small monitoring script or dashboard that tracks key indicators (such as number of cases processed per day, or detection of any pipeline crashes). This will catch issues early. By the end of week 6, we expect to fully hand over operations to v2.

## Post-Launch Communication

With the new system in place, communication is key for transparency and stakeholder confidence:

*   **Documentation Update:** Publish a detailed changelog or technical note describing the changes in v2 (what’s new: API integration, better data quality, etc.) and how it affects users. For example, if the data format in the DuckDB has changed or improved, document that. The README and docs will note that the project is now on v2 and highlight the benefits (more courts, more reliable data) for users.
*   **Notify Stakeholders:** If there were users consuming the v1 data or API, inform them of the transition. This could be via a mailing list, a post on the project’s GitHub/wiki, or direct contact with research partners. Emphasize that the dataset source is still the Internet Archive but the internal process changed – ideally, they shouldn’t notice negative differences, only positive ones (like additional courts).
*   **Public Launch/Beta Announcement:** Once confident, announce the “CausaGanha v2” launch on appropriate channels (e.g., a blog post or social media in the legal tech community). This announcement would focus on new capabilities (nationwide coverage, improved accuracy) and invite users to explore the data or interface. If a web dashboard is ready, this is when it can be advertised for public access.
*   **Community Feedback Loop:** Provide a channel for feedback/bug reports (for instance, a GitHub discussions page or email) so early adopters can report any data oddities. This will help catch any subtle issues that weren’t seen in testing. Given the transparency goal, we may also publish a “data validation report” showing some metrics (like distribution of case outcomes, etc.) to show the community that v2 data is consistent and credible.

In summary, the launch plan emphasizes a safe transition (no data interruptions), clear communication, and setting the stage for broader adoption of CausaGanha’s insights once v2 is proven in production.
