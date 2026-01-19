# Technical Requirements & Specifications

This document defines the technical requirements, scale targets, and performance expectations for CausaGanha.

---

## 📊 Scale Targets by Phase

### MVP (6 Months)
| Metric | Target |
|--------|--------|
| Tribunals | 5 |
| Decisions/day | 250-500 |
| Total decisions | 50,000 |
| Lawyers rated | 10,000 |
| LLM cost | $300-500/month |
| Storage | <5 GB |
| Pipeline duration | <6 hours |

### Public Beta (Year 1)
| Metric | Target |
|--------|--------|
| Tribunals | 10 |
| Decisions/day | 5,000-7,000 |
| Total decisions | 500,000 |
| Lawyers rated | 50,000 |
| LLM cost | $2,000-3,000/month |
| Storage | <50 GB |
| Pipeline duration | <12 hours |
| API requests/month | 100,000 |
| API response time | <500ms |

### Public Launch (Year 2)
| Metric | Target |
|--------|--------|
| Tribunals | 30+ |
| Decisions/day | 20,000+ |
| Total decisions | 2,000,000+ |
| Lawyers rated | 150,000+ |
| LLM cost | $10,000/month (or use ML) |
| Storage | <200 GB |
| Pipeline duration | <24 hours |
| API requests/month | 5,000,000 |
| API response time | <200ms |
| Concurrent users | 1,000 |

---

## 🏗️ Architecture Requirements

### MVP Architecture

```
GitHub Actions (Daily Trigger)
         ↓
┌─────────────────────────┐
│  Pipeline Orchestrator  │
└────────┬────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│ Collect│ │ Archive  │
│ (PJe)  │ │ (IA)     │
└───┬────┘ └────┬─────┘
    │           │
    ▼           ▼
┌──────────────────┐
│   DuckDB Store   │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│Analyze │ │ Score  │
│(Gemini)│ │(Skill) │
└────────┘ └────────┘
```

**Technology Stack:**
- **Language:** Python 3.11+
- **Database:** DuckDB (embedded)
- **Query Layer:** Ibis
- **LLM:** Google Gemini 2.0-flash-exp (via Pydantic AI)
- **Async:** asyncio + httpx
- **Logging:** structlog
- **CI/CD:** GitHub Actions
- **Archival:** Internet Archive S3 API
- **Validation:** Pydantic v2

### Post-MVP Architecture (Year 2)

```
┌──────────────┐
│   Users      │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│   FastAPI    │────▶│  PostgreSQL │
│   (API)      │     │  (Primary)  │
└──────┬───────┘     └─────────────┘
       │
       ▼
┌──────────────┐     ┌─────────────┐
│   Redis      │     │   S3/R2     │
│   (Cache)    │     │  (Backups)  │
└──────────────┘     └─────────────┘
       │
       ▼
┌──────────────┐
│  Background  │
│  Pipeline    │
│  (Existing)  │
└──────────────┘
```

---

## ⚡ Performance Requirements

### MVP Performance

| Operation | Requirement | Current |
|-----------|-------------|---------|
| Collection (per tribunal) | <5 min for 100 intimations | ✅ ~3 min |
| Archival (per PDF) | <30 sec | ⏳ TBD |
| Analysis (per decision) | <15 sec | ✅ ~10 sec |
| Scoring (per rating update) | <1 sec | ✅ <1 sec |
| Database query (lawyer lookup) | <100ms | ✅ ~50ms |
| Full pipeline (500 decisions) | <6 hours | ⏳ TBD |

### Post-MVP Performance (Year 2)

| Operation | Requirement |
|-----------|-------------|
| API response (lawyer search) | <200ms (p95) |
| API response (lawyer profile) | <100ms (p95) |
| Database write | <50ms |
| Cache hit rate | >80% |
| Uptime | 99% |

---

## 💾 Data Storage Requirements

### Database Schema

**Tables:**
1. `intimations` - Raw court intimations (~1KB/row)
2. `intimation_lawyers` - Lawyer associations (~200B/row)
3. `decision_analysis` - LLM extractions (~500B/row)
4. `lawyer_ratings` - Current ratings (~300B/row)
5. `sync_log` - Pipeline execution history (~500B/row)
6. `monitored_courts` - Tribunal configuration (~200B/row)

**Indexes:**
- intimations(hash) - duplicate detection
- intimations(sigla_tribunal, data_disponibilizacao) - collection queries
- intimation_lawyers(oab, state) - lawyer lookups
- lawyer_ratings(oab, state, tribunal) - rating queries
- decision_analysis(intimation_id) - foreign key

### Storage Growth Projections

| Phase | Decisions | Lawyers | DB Size | Archive Size |
|-------|-----------|---------|---------|--------------|
| MVP | 50K | 10K | 5 GB | 50 GB PDFs |
| Year 1 | 500K | 50K | 50 GB | 500 GB PDFs |
| Year 2 | 2M | 150K | 200 GB | 2 TB PDFs |

**Retention Policy:**
- Raw intimations: Permanent
- Analyses: Permanent
- Ratings history: Permanent (audit trail)
- Logs: 90 days
- PDFs: Permanent (Internet Archive)

---

## 🔒 Security Requirements

### MVP Security

**Authentication:**
- No user authentication (internal tool only)
- GitHub Actions via secrets
- Internet Archive API keys via environment variables

**Data Protection:**
- Database: Local file, no public access
- Secrets: GitHub Secrets, environment variables
- No PII encryption needed (all public data)

**API Security (Post-MVP):**
- API keys for authentication
- Rate limiting per key
- HTTPS only
- CORS restrictions

### Compliance

**LGPD (Brazilian GDPR):**
- Legal basis: Legitimate interest (public transparency)
- Data minimization: Only public court data
- Right to rectification: Dispute mechanism (Phase 2)
- Right to deletion: Complex - balance with transparency
- Security: Access controls, audit logs

---

## 🌐 Infrastructure Requirements

### MVP Infrastructure

**Compute:**
- GitHub Actions (2,000 minutes/month free tier)
- Pipeline runs: ~4 hours/day = ~120 hours/month = 7,200 minutes/month
- **Cost:** $0 (within free tier)

**Storage:**
- DuckDB: Local file system
- GitHub repo: <1 GB
- **Cost:** $0

**External Services:**
- Gemini API: $300-500/month
- Internet Archive: Free
- Domain: $15/year
- **Total:** ~$500/month

### Year 2 Infrastructure

**Compute:**
- VPS or cloud VM (4 vCPU, 8 GB RAM): $50/month
- Background workers (pipeline): $30/month
- **Cost:** $80/month

**Storage:**
- PostgreSQL (managed): $25/month
- S3/R2 (backups): $20/month
- **Cost:** $45/month

**CDN & Cache:**
- Cloudflare (free tier)
- Redis (managed): $20/month
- **Cost:** $20/month

**Total:** ~$150/month + LLM costs

---

## 🚀 Scalability Requirements

### Horizontal Scaling (Year 2+)

**Pipeline:**
- Parallelize tribunal collection (10 courts concurrently)
- Batch LLM requests (10 decisions per batch)
- Async I/O throughout
- Multi-process scoring (DuckDB allows concurrent reads)

**API:**
- Stateless FastAPI (can add replicas)
- Redis cache layer
- Database connection pooling
- Read replicas for queries

**Bottlenecks to Watch:**
1. **LLM API rate limits** - Solution: ML prediction
2. **Database writes** - Solution: Batch inserts
3. **Internet Archive uploads** - Solution: Async queue
4. **GitHub Actions minutes** - Solution: Self-hosted runners

---

## 📈 Monitoring Requirements

### MVP Monitoring

**Metrics to Track:**
- Pipeline execution time per stage
- Success/failure counts per stage
- LLM API response times
- Database query times
- Error rates

**Alerting:**
- Email on pipeline failure
- Email on error rate >10%
- Daily summary email

**Tools:**
- structlog for logging
- Custom metrics in logs
- GitHub Actions notifications

### Year 2 Monitoring

**Metrics:**
- API latency (p50, p95, p99)
- Error rates per endpoint
- Database performance
- Cache hit rates
- Uptime
- User analytics

**Tools:**
- Prometheus + Grafana
- Sentry for error tracking
- Uptime monitoring (UptimeRobot)
- Analytics (PostHog or Plausible)

---

## 🧪 Testing Requirements

### MVP Testing

**Unit Tests:**
- Coverage: >80% for core logic
- Test: Pydantic models, scoring algorithm, validators
- Framework: pytest

**Integration Tests:**
- Test: Full pipeline with mock data
- Test: LLM integration with sample PDFs
- Test: Database operations

**BDD Tests:**
- 329 scenarios across 10 feature files
- Framework: pytest-bdd
- Coverage: All user-facing behaviors

**Manual Testing:**
- 500-case validation for accuracy
- End-to-end pipeline test (30 days)

### Year 2 Testing

**Additional Tests:**
- Load testing (API with 1000 concurrent users)
- Security testing (OWASP Top 10)
- Performance regression tests
- End-to-end user journey tests

---

## 🔄 Deployment Requirements

### MVP Deployment

**CI/CD:**
- GitHub Actions workflow
- Triggers: Daily cron (2 AM UTC)
- Triggers: Manual dispatch
- Secrets: Gemini API key, IA credentials

**Deployment Steps:**
1. Install dependencies (uv sync)
2. Run database migrations (if needed)
3. Execute pipeline (causaganha pipeline)
4. Log results
5. Send summary email

**Rollback:**
- Git revert
- Database: DuckDB file backups (daily)
- Manual re-run of pipeline

### Year 2 Deployment

**Infrastructure as Code:**
- Terraform or Docker Compose
- Automated deployments
- Blue/green deployments
- Database migrations (Alembic)

---

## ⚙️ Configuration Management

### Environment Variables

**Required (MVP):**
```bash
GEMINI_API_KEY=<api-key>
IA_ACCESS_KEY=<internet-archive-access>
IA_SECRET_KEY=<internet-archive-secret>
DATABASE_PATH=/path/to/causaganha.duckdb
LOG_LEVEL=INFO
```

**Optional:**
```bash
DRY_RUN=false
COURTS=TJRO,TJAC,TJAP
LOOKBACK_DAYS=7
BATCH_SIZE=10
MAX_BATCHES=100
```

### Configuration Files

**Monitored Courts:**
```yaml
# config/courts.yaml
courts:
  - code: TJRO
    enabled: true
    lookback_days: 7
  - code: TJAC
    enabled: true
    lookback_days: 7
```

---

## 📝 Documentation Requirements

### MVP Documentation

**Required:**
1. ✅ README.md - Project overview
2. ✅ CLAUDE.md - Development guide
3. ✅ docs/PRODUCT_VISION.md
4. ✅ docs/MVP_SCOPE.md
5. ✅ docs/ROADMAP.md
6. ⏳ OPERATIONS.md - How to run the pipeline
7. ⏳ METHODOLOGY.md - How ratings are calculated
8. ⏳ API.md - API documentation (Phase 2)

**Code Documentation:**
- Docstrings for all public functions
- Type hints (Python 3.11+)
- README in each major module

---

## 🎯 Success Metrics

### Technical KPIs (MVP)

| KPI | Target | Measurement |
|-----|--------|-------------|
| Pipeline Success Rate | >95% | Successful runs / total runs |
| Analysis Accuracy | >85% | Manual validation |
| LLM Confidence | >0.80 avg | Average confidence score |
| Error Rate | <5% | Errors / total operations |
| Pipeline Duration | <6 hours | End-to-end time |
| Database Query Time | <100ms | Average lawyer lookup |
| Cost Efficiency | <$1 per 1000 analyses | Total cost / analyses |

---

**Last Updated:** 2025-01-19
**Status:** MVP specifications active
**Next Review:** Month 6 (before Public Beta)
