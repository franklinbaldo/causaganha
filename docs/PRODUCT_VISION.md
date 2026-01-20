# CausaGanha Product Vision

![Status](https://img.shields.io/badge/status-MVP%20Development-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-v2.0-orange?style=for-the-badge)

> **Mission:** Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

---

## 🎯 The Problem We Solve

### Primary Problem: Information Asymmetry
Right now, choosing a lawyer in Brazil is based on:
- 🤝 Personal referrals (limited network)
- 📢 Advertising budget (not competence)
- 🎲 Luck (no objective data)

**Result:** Regular citizens and small businesses cannot evaluate lawyer competence objectively.

### The Insight
We're creating the **"Elo rating for lawyers"** - objective, data-driven, transparent performance metrics based on actual case outcomes.

---

## 👥 Who We Serve

### Primary User: Maria - The Legal Consumer
- **Profile:** 35-year-old teacher filing a labor lawsuit
- **Goal:** Find a competent labor lawyer without expensive referrals
- **Pain Point:** "All lawyers say they're the best - how do I know who to trust?"
- **Success:** Maria finds a lawyer with a 65%+ win rate in labor cases in her state

### Secondary User: Dr. João - The Lawyer
- **Profile:** 42-year-old civil lawyer in São Paulo
- **Goal:** Build reputation based on merit, not marketing budget
- **Pain Point:** "Junior lawyers with rich clients get more business than experienced lawyers with results"
- **Success:** João's rating increases after winning complex cases, attracting better clients

### Secondary User: Professor Ana - The Researcher
- **Profile:** Legal academic studying judicial system efficiency
- **Goal:** Access structured data on judicial decisions for research
- **Pain Point:** "Court data is fragmented, unstructured, and disappears over time"
- **Success:** Ana downloads 5 years of TJSP decisions via API for research

---

## 🚀 What Success Looks Like

### 6-Month Success Metrics (MVP)
- ✅ **Coverage:** 5-10 state tribunals with daily automated collection
- ✅ **Data:** 50,000+ decisions analyzed and 10,000+ lawyers rated
- ✅ **Quality:** >90% accuracy on LLM analysis (validated via manual sampling)
- ✅ **Preservation:** All decisions archived to Internet Archive
- ✅ **Proof of concept:** 1-2 media articles or research papers citing CausaGanha data
- ✅ **Technical:** Pipeline runs reliably daily via GitHub Actions without manual intervention

### Year 1 Success Metrics
- **Coverage:** 10 tribunals (including TJSP)
- **Data:** 500,000+ decisions, 50,000+ lawyers
- **Public API:** Available for researchers
- **Media:** Regular citations in legal journalism
- **Credibility:** Recognition from legal transparency community

### Year 2+ Success Metrics
- **Coverage:** 30+ tribunals
- **Users:** 100,000+ monthly users
- **Revenue:** $5-10K MRR from B2B API access
- **Impact:** Measurable shift in how Brazilians choose lawyers

---

## 💡 Core Value Proposition

### For Legal Consumers
> "Make informed decisions about legal representation based on actual performance data, not marketing."

**Value Delivered:**
- Objective lawyer ratings based on case outcomes
- Transparent methodology (full audit trail)
- Free access to basic information
- Permanent preservation of source documents

### For Lawyers
> "Build reputation based on merit and results, not advertising budget."

**Value Delivered:**
- Performance recognition for competent lawyers
- Objective, auditable metrics
- Career progression tracking
- Competitive advantage for skilled practitioners

### For Researchers & Transparency Advocates
> "Access comprehensive, structured judicial decision data for analysis and accountability."

**Value Delivered:**
- Structured data via public API
- Historical preservation (Internet Archive)
- Reproducible methodology
- Open data ethos

---

## 🎨 Product Philosophy

### 1. Transparency Above All
- Every rating traces back to source decisions
- Methodology is public and auditable
- All decisions preserved permanently
- Users can verify every claim

### 2. Data-Driven, Not Opinion-Based
- Ratings from actual case outcomes, not reviews
- AI extraction reduces human bias
- Statistical methods (OpenSkill) handle uncertainty
- Confidence intervals shown to users

### 3. Preserve First, Analyze Second
- Internet Archive preservation is non-negotiable
- Legal history must not disappear
- Archival is a core mission, not a feature

### 4. Start Small, Scale Thoughtfully
- Prove with 5 tribunals before expanding to 90
- Validate accuracy before public launch
- Build credibility through transparency community
- Prioritize quality over quantity

---

## 🔄 The Core Loop

```
┌──────────────┐
│   COLLECT    │  Fetch intimations from PJe API (includes texto field)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   ANALYZE    │  Extract winner/loser from texto using Gemini LLM
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    SCORE     │  Calculate lawyer ratings with OpenSkill
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   EXPORT     │  Convert to Parquet (columnar format)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ARCHIVE     │  Upload to Internet Archive (free data lake)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   PUBLISH    │  Share IA URLs for public download & verification
└──────────────┘
```

This loop runs automatically, daily, unattended.

**Key Innovation**: Internet Archive serves as a free, distributed, permanent data lake using Parquet format for efficient queries.

---

## 📊 Business Model

### Phase 1 (Year 1): Free & Open
- **Revenue:** $0
- **Funding:** Grants, public interest organizations
- **Goal:** Build credibility and dataset
- **Users:** Researchers, journalists, transparency advocates

### Phase 2 (Year 2): Freemium
- **Free Tier:** Basic lawyer search and ratings
- **Premium API:** Advanced analytics, bulk data access
- **Target Customers:** Legal tech companies, law firms, insurers
- **Revenue Goal:** $5-10K MRR

### Phase 3 (Year 3+): B2B SaaS
- **White-label Solutions:** License technology to legal platforms
- **Enterprise Analytics:** Custom dashboards for law firms
- **Data Partnerships:** Sell anonymized insights
- **Revenue Goal:** $50K+ MRR

---

## 🏆 Competitive Advantages

### 1. **First Mover in Brazil**
- No existing transparent lawyer rating system
- Difficult to replicate (technical + legal complexity)

### 2. **AI-Powered at Scale**
- Manual analysis doesn't scale to 90 tribunals
- LLM extraction of `texto` field from PJe API
- Automated winner/loser determination

### 3. **Free, Distributed Data Lake**
- Internet Archive as primary database ($0 cost)
- Parquet format (10x compression, fast queries)
- Anyone can download and verify ratings
- No cloud storage costs (vs. $1,200+/year on AWS)

### 4. **Open & Transparent**
- Not a black box algorithm
- Full methodology disclosure builds trust
- Public data lake enables independent verification
- Reproducible science: download Parquet files, recalculate ratings

### 5. **Technical Excellence**
- Modern stack (DuckDB, Ibis, Pydantic AI, Parquet)
- Automated CI/CD pipeline
- Scalable architecture
- Smart partitioning (tribunal + date) for efficient access

---

## ⚠️ Key Risks & Mitigation

### Risk 1: OAB Opposition
**Risk:** Brazilian Bar Association opposes public performance rankings

**Mitigation:**
- Frame as "public transparency" not "advertising"
- Use only public court data
- Engage OAB early, seek partnership
- Legal counsel review

### Risk 2: Data Accuracy Issues
**Risk:** LLM misidentifies winners, corrupts ratings

**Mitigation:**
- 85%+ accuracy threshold (reject low-confidence analyses)
- Manual sampling validation (100 cases/month)
- Lawyer dispute mechanism
- Full audit trail for corrections

### Risk 3: Court API Access Revoked
**Risk:** Courts block our API access

**Mitigation:**
- Respect rate limits and terms of service
- Maintain good relationships
- Have fallback data sources
- Legal right to public data access

### Risk 4: Scalability Challenges
**Risk:** Can't handle 90 tribunals at scale

**Mitigation:**
- Start with 5 tribunals, prove viability
- Modern scalable architecture (DuckDB, async)
- ML prediction reduces LLM costs (if needed)
- Incremental expansion

### Risk 5: LGPD Compliance
**Risk:** Violate Brazilian data protection laws

**Mitigation:**
- Legal basis: "legitimate interest" (public transparency)
- Lawyer dispute/correction mechanisms
- Security best practices
- Legal counsel consultation

---

## 🎯 What We Are NOT

- ❌ **Not a lawyer marketplace** - We don't connect users to lawyers (yet)
- ❌ **Not a review site** - No subjective reviews, only objective outcomes
- ❌ **Not a court analytics tool** - We serve legal consumers, not courts
- ❌ **Not a legal research platform** - We rate lawyers, not analyze case law
- ❌ **Not a black box** - Full transparency and auditability

---

## 📈 North Star Metrics

### Primary Metric: **Ratings Quality**
- Target: 92%+ accuracy on manual validation
- Why: Trust is everything; bad data destroys credibility

### Secondary Metrics:
1. **Coverage Breadth:** Number of tribunals × lawyers rated
2. **Data Freshness:** Lag between decision publication and rating update
3. **User Adoption:** Monthly active users (post-launch)
4. **Media Citations:** Number of journalists/researchers using our data
5. **Pipeline Reliability:** % of days with successful automated runs

---

## 🌟 Vision Statement

> **By 2027, CausaGanha will be the trusted source for lawyer performance data in Brazil, empowering millions to make informed legal decisions and driving accountability in the justice system.**

**Moonshot:** Every Brazilian considering legal representation checks CausaGanha first, just like they check reviews before buying a product.

---

## 📚 Related Documentation

- [Feature Roadmap](./ROADMAP.md) - Prioritized feature development plan
- [User Personas](./PERSONAS.md) - Detailed user profiles and journeys
- [Technical Requirements](./TECHNICAL_REQUIREMENTS.md) - Scale and performance specs
- [MVP Scope](./MVP_SCOPE.md) - Minimum viable product definition
- [Compliance Guide](./COMPLIANCE.md) - Legal and regulatory requirements

---

**Last Updated:** 2025-01-19
**Status:** Active Development (V2 Pipeline)
**Next Review:** Q2 2025
