# Minimum Viable Product (MVP) Scope

**Goal:** Daily automated lawyer ratings for 5 Brazilian tribunals
**Timeline:** 6 months from project start
**Success Metric:** 30 consecutive days of reliable operation + 50K decisions + >90% accuracy

---

## ✅ MVP Features (IN SCOPE)

### Priority 1: Core Pipeline

#### 1.1 Data Collection
- ✅ Automated collection from PJe API for 5 state tribunals
- ✅ Daily scheduled runs via GitHub Actions
- ✅ Tribunals: TJRO, TJAC, TJAP, TJAM, TJRR (Northern states, ~250-500 decisions/day total)
- ✅ 7-day default lookback period
- ✅ Duplicate detection via hash
- ✅ Lawyer association extraction (OAB + state + pole)
- ✅ Pagination handling for large result sets
- ✅ Basic retry logic for transient failures

**Acceptance Criteria:**
- Collect 250-500 intimations/day automatically
- <2% duplicate rate
- Process without manual intervention

#### 1.2 Document Archival
- ✅ Download PDFs from PJe
- ✅ Upload to Internet Archive with metadata
- ✅ Store archive.org URLs in database
- ✅ Verify successful uploads
- ✅ Handle archival failures gracefully

**Acceptance Criteria:**
- 100% of collected decisions archived within 24 hours
- Permanent preservation on archive.org
- Verifiable links stored in database

#### 1.3 Decision Analysis
- ✅ Gemini LLM (2.0-flash-exp) for extraction
- ✅ Extract: winner, loser, decision type, outcome, judge, reasoning
- ✅ Pydantic model validation
- ✅ Confidence scoring (threshold: 0.70 minimum)
- ✅ Batch processing (5-10 decisions per batch)
- ✅ Async/concurrent LLM requests
- ✅ Handle LLM failures and timeouts

**Acceptance Criteria:**
- >85% accuracy (validated via manual sampling of 100 cases)
- Average confidence >0.80
- Process 100+ decisions/day
- <10% analysis failure rate

#### 1.4 Lawyer Scoring
- ✅ OpenSkill (PlackettLuce) algorithm
- ✅ Calculate mu, sigma, conservative estimate
- ✅ Win/loss statistics tracking
- ✅ Tribunal-specific ratings
- ✅ Global ratings (aggregated across tribunals)
- ✅ Handle multi-lawyer teams
- ✅ Update ratings incrementally

**Acceptance Criteria:**
- 10,000+ lawyers rated
- Rating updates within 24 hours of new analyses
- Proper handling of new lawyers (cold start)
- No rating corruption from duplicate processing

### Priority 2: Operations & Reliability

#### 2.1 Pipeline Orchestration
- ✅ Single command to run full pipeline: collect → archive → analyze → score
- ✅ Stage skipping flags (--skip-collect, --skip-archive, etc.)
- ✅ Progress tracking and logging
- ✅ Summary reporting after each run
- ✅ GitHub Actions workflow for daily execution

**Acceptance Criteria:**
- Pipeline completes in <6 hours for daily volume
- <5% overall failure rate
- Clear error reporting

#### 2.2 Error Handling
- ✅ Retry logic with exponential backoff (3 attempts)
- ✅ Graceful degradation (skip failures, continue pipeline)
- ✅ Structured error logging
- ✅ Email alerts on critical failures
- ✅ Partial success handling (process what we can)

**Acceptance Criteria:**
- Pipeline continues after individual failures
- No data corruption from errors
- Clear failure logs for debugging

#### 2.3 Database & Storage
- ✅ DuckDB for persistence
- ✅ Ibis query interface
- ✅ Schema with tables: intimations, intimation_lawyers, decision_analysis, lawyer_ratings, sync_log, monitored_courts
- ✅ Referential integrity constraints
- ✅ Indexes for performance
- ✅ Backup strategy

**Acceptance Criteria:**
- Database queries <100ms for lawyer lookups
- No data loss on crashes
- Automatic schema initialization

#### 2.4 Monitoring & Logging
- ✅ Structured JSON logs (structlog)
- ✅ Log levels: DEBUG, INFO, WARNING, ERROR
- ✅ Timestamp, stage, and context in all logs
- ✅ Basic metrics tracking (counts, timing, errors)
- ✅ Daily summary emails

**Acceptance Criteria:**
- All pipeline runs logged
- Errors include stack traces
- Metrics available for monitoring

### Priority 3: Data Quality

#### 3.1 Validation
- ✅ Case number format validation (CNJ standard)
- ✅ OAB number normalization and validation
- ✅ State code validation (valid Brazilian states)
- ✅ Tribunal code validation (known tribunals)
- ✅ Confidence threshold enforcement (≥0.70)
- ✅ Duplicate detection

**Acceptance Criteria:**
- Invalid data rejected before processing
- Clear validation error messages
- No garbage data in database

#### 3.2 Accuracy Verification
- ✅ Manual sampling process (100 cases/month)
- ✅ Accuracy tracking over time
- ✅ Low-confidence flagging for review

**Acceptance Criteria:**
- >85% accuracy on manual validation
- Accuracy metrics logged and tracked
- Process for identifying and fixing errors

---

## ❌ MVP Features (OUT OF SCOPE - Post-MVP)

### Deferred to Phase 2 (Year 1)

#### User-Facing Features
- ❌ Public website with lawyer search
- ❌ Lawyer profile pages
- ❌ Comparison tool (compare 3 lawyers)
- ❌ User accounts and saved searches
- ❌ Mobile app

**Rationale:** MVP focuses on proving data pipeline works. User interface comes after we have reliable data.

#### Advanced Analytics
- ❌ Lawyer practice area categorization
- ❌ Trend analysis (rating over time)
- ❌ Peer comparison (vs average lawyer)
- ❌ Geographic heatmaps
- ❌ Case difficulty scoring

**Rationale:** Need sufficient data (6-12 months) before analytics are meaningful.

#### ML Winner Prediction
- ❌ Embedding generation
- ❌ Online learner training
- ❌ LLM teacher labeling
- ❌ Bootstrap from historical data

**Rationale:** LLM costs are <$200/month at MVP scale. Optimization not needed yet.

#### Multi-Court Scale
- ❌ 90 tribunals (only 5 for MVP)
- ❌ Federal courts (TRF)
- ❌ Labor courts (TRT)
- ❌ Superior courts (STJ, STF)

**Rationale:** Prove with 5 small tribunals before scaling to 90.

### Deferred to Phase 3 (Year 2+)

#### Compliance Features
- ❌ Lawyer dispute resolution mechanism
- ❌ LGPD data deletion workflow
- ❌ Correction/amendment process
- ❌ Formal audit trails for legal compliance

**Rationale:** Implement when we have public-facing product and real user complaints.

#### Monetization
- ❌ Premium API tiers
- ❌ Advanced analytics dashboards for law firms
- ❌ White-label solutions
- ❌ Enterprise features

**Rationale:** Build free product first, monetize later.

#### Advanced Resilience
- ❌ Multi-region failover
- ❌ Load balancing
- ❌ Auto-scaling
- ❌ 99.9% uptime SLA

**Rationale:** MVP is batch processing (overnight runs). High availability not critical yet.

---

## 🎯 MVP Success Criteria

### Technical Success
1. ✅ **Reliability:** 30 consecutive days without manual intervention
2. ✅ **Coverage:** 5 tribunals collecting daily
3. ✅ **Volume:** 50,000+ decisions analyzed
4. ✅ **Quality:** >85% accuracy on manual validation
5. ✅ **Preservation:** 100% archival to Internet Archive
6. ✅ **Performance:** Pipeline completes in <6 hours

### Data Success
1. ✅ **Lawyers Rated:** 10,000+ unique lawyers
2. ✅ **Rating Quality:** Average confidence >0.80
3. ✅ **Completeness:** >95% of collected intimations analyzed and scored
4. ✅ **Accuracy:** Manual validation confirms >85% correct winner identification

### Operational Success
1. ✅ **Automation:** Runs via GitHub Actions without manual triggers
2. ✅ **Monitoring:** Alerts fire on failures
3. ✅ **Recovery:** Can restart from failures without data loss
4. ✅ **Documentation:** Pipeline operations documented

### Business Success
1. ✅ **Proof of Concept:** 1-2 media articles or research papers cite our data
2. ✅ **Credibility:** Positive feedback from transparency community
3. ✅ **Scalability:** Confident we can expand to 10+ tribunals
4. ✅ **Cost:** LLM costs <$500/month

---

## 📅 MVP Development Timeline

### Month 1-2: Foundation
- ✅ V2 architecture design (DONE)
- ✅ DuckDB + Ibis storage layer (DONE)
- ✅ PJe API client implementation (DONE)
- ✅ Basic collection pipeline (DONE)
- ✅ Schema design and migrations (DONE)

### Month 3: Analysis & Scoring
- ✅ Pydantic AI integration (DONE)
- ✅ Gemini LLM analyzer (DONE)
- ✅ OpenSkill scoring implementation (DONE)
- ⏳ Accuracy validation process
- ⏳ Confidence threshold tuning

### Month 4: Archival & Pipeline
- ⏳ Internet Archive integration
- ⏳ End-to-end pipeline orchestration
- ⏳ GitHub Actions workflow
- ⏳ Error handling and retry logic
- ⏳ Multi-court configuration

### Month 5: Quality & Reliability
- ⏳ Data quality validation
- ⏳ Manual sampling process
- ⏳ Monitoring and alerting
- ⏳ Performance optimization
- ⏳ Edge case handling

### Month 6: Testing & Launch
- ⏳ 30-day automated run test
- ⏳ Manual validation of 500 analyses
- ⏳ Bug fixes and refinements
- ⏳ Documentation completion
- ✅ **MVP Launch:** Pipeline running reliably

---

## 🚀 Post-MVP Roadmap

### Phase 2: Public Beta (Months 7-12)
**Goal:** Make data accessible to researchers and transparency advocates

**Features:**
- Public API for researchers
- Basic website with data browser
- Documentation and methodology page
- Researcher onboarding process

**Success Metrics:**
- 10 tribunals
- 500,000 decisions
- 50,000 lawyers
- 10+ research papers using data

### Phase 3: Public Launch (Months 13-18)
**Goal:** User-facing lawyer search for legal consumers

**Features:**
- Lawyer search and filter
- Profile pages
- Comparison tool
- SEO optimization

**Success Metrics:**
- 100,000 monthly users
- Media coverage
- User testimonials

### Phase 4: Monetization (Months 19-24)
**Goal:** Sustainable revenue model

**Features:**
- Premium API tiers
- Advanced analytics
- B2B partnerships

**Success Metrics:**
- $5-10K MRR
- 5+ paying customers
- Profitable unit economics

---

## 🔍 MVP Scope Decisions Rationale

### Why 5 Tribunals, Not 1 or 90?
- **1 tribunal = demo, not product:** Need multi-court to prove scalability
- **90 tribunals = premature optimization:** Risk spreading too thin before validation
- **5 tribunals = sweet spot:** Enough to prove multi-court works, small enough to debug

### Why Northern States (TJRO, TJAC, etc.)?
- **Lower volume:** Easier to debug and validate (~50-100 decisions/day each)
- **PJe API availability:** All use standardized PJe system
- **Underserved markets:** Less legal tech presence, higher impact
- **Geographic diversity:** Spread across region

### Why Internet Archive, Not S3?
- **Mission alignment:** Transparency and permanence
- **Zero cost:** Free for nonprofit use
- **Credibility:** archive.org is trusted by researchers
- **Permanence:** True long-term preservation

### Why OpenSkill, Not ELO?
- **Handles uncertainty:** Sigma parameter for new lawyers
- **Team support:** Multi-lawyer cases
- **No inflation:** Ratings stabilize over time
- **Proven:** Used in chess, esports

### Why Gemini, Not GPT-4?
- **Native PDF reading:** No extraction needed
- **Cost:** Flash model is very cheap (~$0.0006/analysis)
- **Performance:** Fast inference times
- **Pydantic AI support:** Built-in integration

### Why No ML Prediction in MVP?
- **Cost not a constraint:** LLM is <$200/month at MVP scale
- **Complexity tradeoff:** ML adds significant complexity
- **Premature optimization:** Optimize after validating core pipeline

---

## ✅ Definition of "Done" for MVP

**The MVP is complete when:**

1. ✅ Pipeline runs automatically every day for 30 consecutive days
2. ✅ Collects from 5 tribunals (TJRO, TJAC, TJAP, TJAM, TJRR)
3. ✅ Analyzes 50,000+ total decisions
4. ✅ Rates 10,000+ lawyers
5. ✅ Archives 100% to Internet Archive
6. ✅ Achieves >85% accuracy on 500-case manual validation
7. ✅ Error rate <5% per stage
8. ✅ Pipeline completes in <6 hours
9. ✅ Monitoring alerts work correctly
10. ✅ Documentation complete (operations, methodology, API)

**At that point, we have proven:**
- ✅ The technical approach works
- ✅ We can scale to more tribunals
- ✅ The data quality is sufficient for public use
- ✅ The system is reliable enough for daily operation

**Then we're ready for Phase 2: Public Beta**

---

## 📊 Resource Requirements for MVP

### Development Time
- **1 senior engineer:** 6 months full-time
- **1 part-time data analyst:** 2 days/week for validation
- **1 legal advisor:** Consulting basis (LGPD, OAB review)

### Infrastructure Costs
- **LLM (Gemini):** ~$300-500/month
- **Compute (GitHub Actions):** Free tier sufficient
- **Storage (DuckDB):** Local, free
- **Internet Archive:** Free
- **Domain/Hosting:** ~$50/month
- **Total:** ~$400-600/month

### Success Budget
- **Development:** Covered (existing team)
- **Operations:** <$1,000/month
- **Marketing:** $0 (stealth mode)
- **Legal:** $2,000 one-time consultation

**Total MVP Budget:** <$10,000

---

**Last Updated:** 2025-01-19
**Status:** Month 3-4 (Analysis & Archival in progress)
**Next Milestone:** Complete archival integration (Month 4)
