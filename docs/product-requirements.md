# Product Requirements Document (PRD)

## Problem Statement

Legal case outcomes and lawyer performance data in Brazil are fragmented and difficult to access. Court decisions are buried in daily judicial gazettes (“diários”), making it hard for citizens, researchers, or lawyers to assess how often a particular lawyer wins cases or identify patterns in judicial decisions. CausaGanha addresses this gap by aggregating judicial decisions and extracting structured insights, creating transparent, data-driven lawyer performance rankings from actual case results. In short, it turns raw court outcomes into actionable analytics, solving the lack of accessible performance metrics in the justice system.

## Target Users

* **Legal Researchers** – need bulk data on case outcomes and lawyer success rates for academic studies.
* **Journalists & Watchdogs** – seek transparency and accountability, using objective lawyer rankings to inform reporting.
* **General Public & Citizens** – want to evaluate lawyers based on track record through open data.
* **Legal Professionals (Lawyers/Firms)** – can benchmark their performance and identify trends via unbiased analytics.

## Proposed Solution

CausaGanha provides an end-to-end pipeline that collects, analyzes, rates, and publishes judicial case data:

1. **Collect** – Gather case metadata and decisions from court APIs (initially the TJRO PJe API) instead of brittle web scraping. This yields structured data (case IDs, involved lawyers, etc.) for each published decision.
2. **Archive** – Download official decision documents (PDFs) and archive them in a public repository (the Internet Archive) for transparency and preservation.
3. **Analyze** – Use AI (LLM) to read the decision text and determine outcomes (e.g. which party won, lawyer wins/losses) in an automated but validated manner. Extract key fields like lawyer names, victory/defeat, case topics, etc.
4. **Score** – Apply the OpenSkill rating algorithm (similar to Elo ratings in chess) to update each lawyer’s performance score based on case outcomes. This produces a rankings database of lawyers, reflecting wins/losses adjusted for case difficulty (OpenSkill provides a probabilistic skill rating).
5. **Distribute** – Store results in an analytical database (DuckDB) and publish snapshots openly. The Internet Archive serves as the distribution channel for database snapshots and files, ensuring anyone can download the data and verify results.

Through this pipeline, CausaGanha delivers an automated “analytics engine” for judicial outcomes: from raw court data to public, queryable insights.

## Scope and Features

* **Jurisdiction Coverage** – Initially covers Tribunal de Justiça de Rondônia (TJRO), with plans to extend to all 90+ courts using Brazil’s PJe system. The system is built to be extensible, supporting multi-tribunal data collection as new courts are onboarded.
* **Data Pipeline** – A modular CLI pipeline (collect → archive → analyze → score) that can run for specified date ranges and courts. Users (or automated schedules) can run the pipeline to continuously update the dataset. The pipeline ensures each stage’s outputs are persisted (e.g. collected metadata, archived PDFs, analysis results, updated ratings) for reliability.
* **Analytics Database** – A local DuckDB database stores all structured data: case metadata (“intimations”), analysis outcomes, and lawyer ratings. This enables efficient analytical queries (via SQL or Python data frames) on case counts, win rates, lawyer rankings, etc., without heavy memory usage (DuckDB is an in-process analytical DB).
* **CLI and (Planned) Dashboard** – The primary interface is a command-line tool (causaganha CLI) for data engineers or developers. Planned future work includes a simple web dashboard or API (FastAPI-based) for a more user-friendly view of key metrics, focusing on read-only statistics and monitoring.
* **AI Integration** – Uses large language models (via Google’s Gemini or similar, through a provider-agnostic Pydantic-AI layer) to interpret decision texts. The AI outputs are constrained into structured Pydantic models (e.g. identifying the winning party, lawyers involved) for consistency. A prompt versioning strategy will be implemented to manage and audit the LLM prompts as the AI analysis evolves.

## User Stories

* As a **legal researcher**, I want to easily query a database of thousands of court decisions to find patterns (like how often certain arguments succeed), so that I can produce quantitative research on judicial outcomes.
* As a **journalist**, I want an automated way to identify which lawyers consistently win cases and which courts have unusual decision patterns, so that I can investigate potential biases or notable performances.
* As a **citizen**, I want to see a ranking or track record of lawyers based on actual case wins and losses, so that I can make an informed choice when hiring a lawyer and trust that the data is objective and publicly available.
* As a **lawyer**, I want to benchmark my success rate against peers in my region, so that I can highlight my performance to clients or identify areas for improvement based on data-driven feedback.

## Success Metrics

CausaGanha’s success will be measured by both data coverage and system reliability:

* **Court Coverage** – Number of courts integrated. Goal: At least 10 courts by end of Q1 2025 (up from 1 currently), on track to eventually cover all major Brazilian courts (90+).
* **Data Capture Rate** – Percentage of published decisions successfully ingested. Goal: >95% of available intimations are captured from each monitored court (minimizing missed cases).
* **Analysis Accuracy** – Quality of AI-extracted outcomes. Goal: ≥90% accuracy in determining case winners and correctly associating lawyers. This will be measured by manual review of samples.
* **Performance** – Throughput of the pipeline. Goal: Able to process 1000+ decisions in under 30 minutes on modest hardware, allowing daily updates to run efficiently.
* **Reliability** – Pipeline robustness and uptime. Goal: 100% successful run rate for scheduled pipeline runs (no crashes), and minimal downtime. For data collection specifically, target 99% uptime (failed API calls retried or <1% of attempts fail).
* **Open Access** – All processed data and methodology published openly. Success means a complete public dataset (e.g. DuckDB file) is updated regularly and accessible to anyone (via Internet Archive), with documentation for reproducibility.

Additionally, internal quality gates ensure the project’s health: e.g. achieving >60% test coverage in early phases (target 80% as the project matures) and 100% CLI command success in testing.

## Non-Goals

To clarify scope, CausaGanha will not focus on certain areas:

* **Lawyer Notification or Case Tracking** – It’s not a real-time notification system for lawyers about their cases (no reminders or case management).
* **Document Management** – Not a general document storage/retrieval system for all legal files; it archives only what’s needed for analytics (court diaries and related data).
* **Legal Deadline Management** – Does not manage procedural deadlines or court schedules for law firms.
* **Legal Advice or Outcome Prediction** – It provides data and rankings, but doesn’t offer legal advice or predictive case outcomes to users.
* **Personal Data Publication** – Will not expose sensitive personal data beyond what is publicly available in decisions, and will follow privacy regulations (e.g. anonymizing as required).

These non-goals ensure the project remains focused on its core mission: judicial analytics and transparency, rather than becoming a general-purpose legal tech platform.

## Constraints and Considerations

* **External API Dependency** – CausaGanha relies on the PJe Comunica API for case metadata. If the API changes or goes down, data collection is blocked. (In V1, scraping HTML/PDF was brittle; V2 improves this by using a stable API, but still depends on external uptime.) The PJe API is also geo-restricted – requests from outside Brazil may be blocked, meaning deployments must run on approved networks or use proxies.
* **Internet Archive Integration** – Uploading files to the Internet Archive requires network access and API keys. Archive uploads can be slow and are rate-limited; large-scale backlogs might require careful queuing. A single-master archive strategy is used (one IA item for all data) to simplify management. We must ensure files and metadata conform to IA’s requirements.
* **Data Privacy and Compliance** – The system processes public court documents, which may include personal information. We must comply with privacy laws (e.g. GDPR) and ethical guidelines. Anonymization hooks and PII management are in place in the pipeline to redact sensitive data if needed. Data retention policies dictate that only necessary data is kept long-term, with snapshots in IA serving archival purposes.
* **Accuracy vs. Cost Trade-offs** – Using LLMs for analysis can be expensive at scale. The design uses metadata from the API to cut down on unnecessary AI calls (e.g. if outcome can be inferred from structured data). OpenSkill rating is computationally cheap, but LLM usage will be optimized (e.g. by batching or using smaller models) to keep cloud costs sustainable.
* **Technical Constraints** – The entire pipeline is implemented in Python and runs on local or cloud compute. Memory and storage must handle large PDF texts and a growing DuckDB file. DuckDB is chosen for its efficiency, but we must monitor database file size and performance as data scales (e.g. consider partitioning or periodic cleanup). Also, as an alpha-stage project, breaking changes are expected; versioning of data schema and prompts is planned to manage transitions.

By recognizing these constraints, the team can mitigate risks (for example, by building robust error handling for API failures, adding caching for AI calls, and adhering to security best practices in handling keys and personal data).
