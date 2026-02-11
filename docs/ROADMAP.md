# CausaGanha Product Roadmap

**Vision:** Transparent lawyer performance ratings for all of Brazil
**Timeline:** 24-month roadmap from MVP to monetization

---

## 🗺️ Roadmap Overview

```
MVP (6mo) → Public Beta (12mo) → Public Launch (18mo) → Monetization (24mo)
    ↓              ↓                    ↓                      ↓
5 courts      10 courts           30 courts              50+ courts
50K dec       500K dec            2M dec                 5M+ dec
10K lawyers   50K lawyers         150K lawyers           300K+ lawyers
Internal      Researchers         Consumers              B2B Revenue
```

---

## 📍 Phase 1: MVP (Months 1-6) ✅ IN PROGRESS

**Goal:** Prove the core pipeline works reliably

### Features
- ✅ Data collection from all 91 tribunals (National coverage)
- ✅ LLM-powered analysis of `texto` field (Gemini)
- ✅ OpenSkill ratings
- ✅ Parquet export with deterministic UUIDv5 identifiers
- ✅ Internet Archive data lake (free permanent storage)
- ✅ Automated pipeline via Single Orchestrator (every 20 min)
- ✅ Basic monitoring and Telegram alerting

### Success Metrics
- 30 days of reliable automated operation
- 50,000+ decisions analyzed
- 10,000+ lawyers rated
- >85% accuracy validated
- <$500/month operational costs

### Deliverables
- Functional pipeline
- Documentation (operations, methodology)
- Validation dataset (500 manually reviewed cases)

**Status:** Month 3-4, archival integration in progress

---

## 📍 Phase 2: Public Beta (Months 7-12)

**Goal:** Make data accessible to transparency community

### Features

#### 2.1 Data Access
- Public API for researchers (read-only)
- API documentation (OpenAPI spec)
- Data export tools (CSV, JSON)
- Rate limiting and authentication

#### 2.2 Tribunal Expansion
- Add 5 more tribunals (total: 10)
- Include TJSP (São Paulo - largest tribunal)
- Federal courts (TRF2, TRF3)
- Labor courts (TRT2, TRT15)

#### 2.3 Website (Minimal)
- Homepage with project explanation
- Methodology documentation
- Data browser (view decisions, ratings)
- Search by OAB number or lawyer name
- No user accounts yet

#### 2.4 Quality Improvements
- Increase accuracy to >90%
- Manual review workflow for flagged cases
- Lawyer dispute submission form (email)
- Quarterly accuracy reports

### Success Metrics
- 10 tribunals collecting daily
- 500,000 total decisions
- 50,000 lawyers rated
- 10+ research papers/articles using data
- 1,000+ API requests/month
- Media coverage (5+ articles)

### Partnerships
- Academic institutions (provide data for research)
- Transparency NGOs (amplify mission)
- Legal tech events (present methodology)

**Timeline:** 6 months (Months 7-12)

---

## 📍 Phase 3: Public Launch (Months 13-18)

**Goal:** User-facing product for legal consumers

### Features

#### 3.1 User-Facing Search
- Lawyer search with filters:
  - Practice area (labor, civil, criminal, etc.)
  - Location (state, city)
  - Minimum cases (credibility threshold)
  - Rating range
- Sort by rating, win rate, or experience
- Pagination and infinite scroll

#### 3.2 Lawyer Profiles
- Public profile page per lawyer (e.g., `/lawyer/123456-SP`)
- Display: rating, win rate, case count, confidence
- Case history (anonymized, linked to archive.org)
- Charts: rating over time, win rate by case type
- SEO-optimized for Google search

#### 3.3 Comparison Tool
- Compare up to 3 lawyers side-by-side
- Tabular comparison of all metrics
- Highlight differences
- Shareable comparison links

#### 3.4 Transparency Features
- "How ratings are calculated" explainer
- Interactive OpenSkill demo
- Methodology paper (PDF download)
- Audit trail: every rating → cases → PDFs
- Data quality dashboard (public)

#### 3.5 Additional Tribunals
- Expand to 30 tribunals
- Cover all major state capitals
- Priority: TJRJ, TJMG, TJRS, TJPR, TJSC, TJBA

### Marketing & Growth
- SEO optimization for "melhores advogados [area] [city]"
- Content marketing (blog posts, guides)
- PR campaign (press release, media outreach)
- Social media presence
- Partnerships with legal aid organizations

### Success Metrics
- 30 tribunals
- 2,000,000 decisions
- 150,000 lawyers
- 100,000 monthly users
- 50+ media mentions
- 20+ research citations

**Timeline:** 6 months (Months 13-18)

---

## 📍 Phase 4: Monetization (Months 19-24)

**Goal:** Sustainable revenue model

### Features

#### 4.1 Premium API
**Free Tier:**
- 1,000 requests/month
- Basic endpoints (search, lawyer profile)
- Rate limited

**Premium Tier ($99/month):**
- 100,000 requests/month
- Bulk data export
- Historical data access
- Webhooks for new data
- Priority support

**Enterprise Tier ($999/month):**
- Unlimited requests
- White-label options
- Custom integrations
- SLA guarantees
- Dedicated account manager

#### 4.2 Advanced Analytics (B2B)
**For Law Firms ($299/month):**
- Track your lawyers' ratings
- Benchmarking vs competitors
- Client-facing reports
- Case outcome predictions

**For Legal Tech Companies ($499/month):**
- Embed ratings in your platform
- Co-branded lawyer search
- API integration
- Revenue sharing model

#### 4.3 Compliance Features
- LGPD compliance dashboard
- Lawyer dispute resolution workflow
- Correction/amendment process
- Audit logs for legal compliance
- Data deletion requests

#### 4.4 ML Winner Prediction
- Implement ML prediction to reduce LLM costs at scale
- Bootstrap from 500K+ labeled decisions
- Target: 80% of analyses via ML, 20% via LLM
- Cost savings: $5,000+/month at scale

### Revenue Targets
- **MRR Goal:** $5-10K
- **Customers:** 50 paying API users, 20 law firms, 5 legal tech companies
- **Unit Economics:** >70% gross margin

### Success Metrics
- Revenue: $5K+ MRR
- Churn: <5% monthly
- Customer satisfaction: >80% NPS
- 50+ tribunals
- 5,000,000+ decisions

**Timeline:** 6 months (Months 19-24)

---

## 📍 Phase 5: Scale & Sustainability (Year 3+)

**Goal:** Comprehensive national coverage and profitability

### Features
- All 90+ Brazilian tribunals
- 10M+ decisions
- 500K+ lawyers
- Mobile apps (iOS, Android)
- Advanced ML features
- International expansion (other Latin American countries?)

### Revenue Target
- $50K+ MRR
- Profitability
- Team expansion (5-10 people)

---

## 🎯 Feature Prioritization Framework

### Priority 1 (Must-Have)
Features without which the product doesn't work:
- Data collection pipeline
- LLM analysis
- Ratings calculation
- Internet Archive preservation

### Priority 2 (Should-Have)
Features essential for public launch:
- Multi-tribunal support (10+)
- Public API
- Basic website/search
- Error handling

### Priority 3 (Nice-to-Have)
Features that enhance but aren't critical:
- ML prediction
- Advanced analytics
- Comparison tool
- Mobile apps

### Priority 4 (Won't-Have Yet)
Features deferred to later phases:
- User accounts and personalization
- Lawyer marketing tools
- Court analytics
- International expansion

---

## 🔄 Revised Priorities Based on PO Feedback

### Moved UP in Priority

**Multi-Court Coverage:** P3 → P2
- Rationale: Single tribunal = demo, not product
- Scope: 10 tribunals (not 90) for credibility
- Timeline: Phase 2 (Public Beta)

**Error Handling:** P3 → P2
- Rationale: Must run unattended daily
- Scope: Basic resilience, graceful degradation
- Timeline: MVP (Phase 1)

### Moved DOWN in Priority

**ML Winner Prediction:** P3 → P4
- Rationale: LLM costs <$500/month at MVP scale
- Scope: Optimize only when costs exceed $2K/month
- Timeline: Phase 4 (Monetization)

**Performance Monitoring (Advanced):** P4 → P4
- Rationale: Basic logs sufficient initially
- Scope: Simple metrics, no dashboards yet
- Timeline: Phase 3 (Public Launch)

---

## 📊 Roadmap Metrics Dashboard

| Phase | Timeline | Tribunals | Decisions | Lawyers | Users | Revenue |
|-------|----------|-----------|-----------|---------|-------|---------|
| MVP | M1-6 | 5 | 50K | 10K | 0 | $0 |
| Beta | M7-12 | 10 | 500K | 50K | 1K | $0 |
| Launch | M13-18 | 30 | 2M | 150K | 100K | $0 |
| Monetize | M19-24 | 50 | 5M | 300K | 250K | $10K |
| Scale | Y3+ | 90+ | 10M+ | 500K+ | 1M+ | $50K+ |

---

## 🚧 Risks & Mitigation

### Risk 1: OAB Opposition
**Mitigation:** Early engagement, transparency, legal counsel

### Risk 2: Accuracy Issues
**Mitigation:** Continuous validation, dispute mechanism, conservative thresholds

### Risk 3: Court API Access Revoked
**Mitigation:** Respect terms of service, maintain relationships, legal right to public data

### Risk 4: Can't Scale
**Mitigation:** Start small (5 tribunals), prove viability, optimize architecture

### Risk 5: No User Adoption
**Mitigation:** Start with researchers/journalists (easier market), build credibility, then consumers

---

## 🎯 Decision Framework

When deciding what to build next, ask:

1. **Does it serve the core mission?** (Transparency and informed decisions)
2. **Does it move us toward the next milestone?** (MVP → Beta → Launch → Monetization)
3. **Can we validate it quickly?** (Prefer testable hypotheses)
4. **What's the cost/impact ratio?** (High impact, low effort = prioritize)
5. **Does it require the previous phase?** (Dependencies matter)

---

**Last Updated:** 2025-01-19
**Status:** Phase 1 (MVP) in progress
**Next Review:** End of Month 6 (MVP completion)
