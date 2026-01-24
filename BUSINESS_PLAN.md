# CausaGanha Business Plan

## Executive Summary

**CausaGanha** is a judicial analytics platform that provides transparent lawyer performance ratings based on real case outcomes from Brazil's electronic court records (DJEN).

**Mission**: Eliminate information asymmetry in the Brazilian legal market.

**Value Proposition**: For the first time, citizens and companies can make informed decisions when hiring lawyers, based on actual performance data rather than marketing claims.

---

## Market Opportunity

### The Problem

1. **Information Asymmetry**: When hiring a lawyer, clients have no objective way to evaluate competence
2. **Trust Deficit**: 74% of Brazilians don't trust the legal system (DataFolha, 2023)
3. **Market Inefficiency**: Good lawyers struggle to differentiate from mediocre ones
4. **High Stakes**: Legal disputes often involve life-changing amounts of money

### Market Size (Brazil)

| Segment | Size | Notes |
|---------|------|-------|
| Legal Services Market | R$ 150B/year | Growing 8% annually |
| Registered Lawyers (OAB) | 1.4M+ | 2nd largest bar in the world |
| New Lawsuits/Year | 30M+ | Highly litigious society |
| Legal Tech Market | R$ 2B | Growing 25% annually |

### Target Market

**Primary**: Individuals seeking lawyers for civil, labor, or consumer cases
**Secondary**: Companies managing legal portfolios
**Tertiary**: Law firms wanting competitive intelligence

---

## Business Model

### Revenue Streams

#### 1. Consumer Subscriptions (B2C)
- **Free**: 5 searches/month, basic ratings
- **Professional**: R$ 97/month - Unlimited searches, detailed ratings, alerts
- Target: Individuals with pending or potential legal cases

#### 2. Enterprise API (B2B)
- **Starter**: R$ 997/month - 10K API calls
- **Professional**: R$ 2,997/month - 50K API calls
- **Enterprise**: Custom pricing - Unlimited
- Target: Legal marketplaces, insurers, corporate legal departments

#### 3. Premium Law Firm Profiles (B2B)
- **Verified Badge**: R$ 297/month - Priority listing, verified badge
- **Featured**: R$ 997/month - Top placement, lead generation
- Target: Law firms wanting to highlight their ratings

#### 4. Data Licensing
- Custom datasets for academic research, government agencies
- Annual contracts: R$ 50K-500K

### Unit Economics (Target)

| Metric | Target |
|--------|--------|
| CAC (Consumer) | R$ 50 |
| LTV (Consumer Pro) | R$ 800 |
| LTV/CAC | 16x |
| Gross Margin | 85% |
| Churn (monthly) | 5% |

---

## Competitive Analysis

### Direct Competitors

| Competitor | Strengths | Weaknesses |
|------------|-----------|------------|
| JusBrasil | Large user base, brand | No performance ratings |
| Aurum | Good CRM for lawyers | Lawyers-only, no public ratings |
| Escavador | Data access | No rating algorithm |

### Our Moat

1. **Unique Data Pipeline**: Continuous scraping of DJEN across all 27 states
2. **OpenSkill Algorithm**: Fair ratings that account for case difficulty
3. **Historical Data**: Years of indexed decisions create compounding value
4. **Network Effects**: More users = more feedback = better ratings

---

## Go-to-Market Strategy

### Phase 1: Validation (Q1 2026)
- Launch landing page with waitlist
- Target: 1,000 waitlist signups
- Conduct user interviews to validate pricing

### Phase 2: Beta (Q2 2026)
- Launch free tier to waitlist
- Implement feedback loop for rating corrections
- Target: 5,000 active users

### Phase 3: Monetization (Q3 2026)
- Launch paid tiers
- Outreach to law firms for verified profiles
- Target: R$ 50K MRR

### Phase 4: Scale (Q4 2026)
- Enterprise API launch
- Partnership with legal marketplaces
- Target: R$ 200K MRR

### Marketing Channels

1. **SEO**: "melhor advogado trabalhista [cidade]"
2. **Content Marketing**: Blog on legal rights, lawyer selection tips
3. **Social Media**: LinkedIn (B2B), Instagram (B2C)
4. **Referral Program**: 1 month free for referrals
5. **PR**: Legal tech press, OAB publications

---

## Technology

### Current Stack

- **Backend**: Python 3.12, DuckDB, Ibis
- **Data Pipeline**: Cloudflare Workers (scraping), Internet Archive (storage)
- **Rating Algorithm**: OpenSkill (similar to Elo)
- **Infrastructure**: GCP Cloud Functions, Firestore

### Development Roadmap

| Quarter | Milestone |
|---------|-----------|
| Q1 2026 | Web frontend, user authentication, search |
| Q2 2026 | API, lawyer dashboard, rating explanations |
| Q3 2026 | Mobile app (PWA), notification system |
| Q4 2026 | Enterprise dashboard, analytics |

---

## Team Requirements

### Immediate Needs (0-3 months)
- **Full-stack Developer**: Build web frontend
- **Data Engineer**: Scale pipeline, improve quality

### Growth Phase (3-12 months)
- **Designer**: UX/UI for consumer app
- **Sales**: Enterprise outreach
- **Support**: Handle lawyer disputes

---

## Financial Projections

### Year 1

| Month | Users | Paid | MRR |
|-------|-------|------|-----|
| 1-3 | 5K | 0 | R$ 0 |
| 4-6 | 20K | 500 | R$ 48K |
| 7-9 | 50K | 2K | R$ 194K |
| 10-12 | 100K | 5K | R$ 485K |

### 3-Year Projection

| Year | ARR | Users | Employees |
|------|-----|-------|-----------|
| 1 | R$ 2M | 100K | 5 |
| 2 | R$ 10M | 500K | 15 |
| 3 | R$ 30M | 1.5M | 40 |

---

## Funding Requirements

### Bootstrap Phase (Current)
- Funding: Self-funded
- Runway: 6 months
- Goal: Validate product-market fit

### Seed Round (Target: Q3 2026)
- Raise: R$ 2M
- Use: Team, marketing, infrastructure
- Metrics needed: 10K active users, R$ 50K MRR

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAB regulatory pushback | High | Proactive engagement, legal opinion |
| Data accuracy challenges | Medium | User feedback loop, dispute resolution |
| Low conversion rates | Medium | A/B testing, pricing experiments |
| Competition from JusBrasil | Medium | Focus on ratings, not content |

---

## Legal Considerations

### Data Sources
- All data from DJEN is public per Lei de Acesso a Informacao (12.527/2011)
- No personal data beyond what is published officially

### LGPD Compliance
- Public interest basis for processing
- Right to rectification for lawyers
- Privacy policy and consent mechanisms

### OAB Regulations
- Ratings based on objective outcomes, not subjective reviews
- No advertising claims, just data presentation

---

## Success Metrics

### Product Metrics
- Monthly Active Users (MAU)
- Searches per user
- Time to conversion (free to paid)
- NPS score

### Business Metrics
- Monthly Recurring Revenue (MRR)
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)
- Churn rate

### Data Quality Metrics
- Rating accuracy (user feedback)
- Data freshness (latency from publication)
- Coverage (% of lawyers with ratings)

---

## Next Steps

1. **Deploy Landing Page**: Set up GitHub Pages for causaganha.com.br
2. **Validate Demand**: Drive traffic and collect 1,000 emails
3. **Build MVP**: Web search interface with basic ratings
4. **Launch Beta**: Invite waitlist users for feedback
5. **Iterate**: Refine ratings based on user input

---

*Last Updated: January 2026*
*Document Version: 1.0*
