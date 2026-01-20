# Legal & Regulatory Compliance

This document outlines legal and regulatory requirements for CausaGanha operations in Brazil.

---

## 🇧🇷 LGPD (Lei Geral de Proteção de Dados)

Brazil's General Data Protection Law (LGPD), effective since 2020, regulates processing of personal data.

### Applicability to CausaGanha

**Personal Data We Process:**
- Lawyer names
- OAB registration numbers
- State of registration
- Case participation history
- Performance metrics (ratings)

**NOT Personal Data:**
- Court decisions (public records)
- Case numbers
- Judicial outcomes
- PDFs (already public)

### Legal Basis for Processing

**Article 7, VI - Legitimate Interest**

CausaGanha processes lawyer data based on "legitimate interest" for the purpose of:
1. Public transparency
2. Consumer protection (informed legal service choices)
3. Legal system accountability

**Balancing Test:**
- ✅ Public interest in transparent lawyer performance
- ✅ Data is already public (court records)
- ✅ Processing is necessary for transparency mission
- ⚠️ Potential lawyer privacy concerns (but public figures in professional capacity)

**Conclusion:** Legitimate interest basis is appropriate.

### LGPD Compliance Requirements

#### 1. Purpose Limitation (Article 6, I)
✅ **Compliant:**
- Data used ONLY for lawyer performance ratings
- No repurposing for marketing, profiling, etc.
- Clear purpose statement on website

#### 2. Data Minimization (Article 6, III)
✅ **Compliant:**
- Collect only: OAB, state, case outcomes
- No addresses, phone numbers, personal details
- No data beyond public court records

#### 3. Transparency (Article 6, VI)
✅ **Compliant:**
- Public methodology documentation
- Clear explanation of how ratings are calculated
- Audit trail (every rating → cases → PDFs)

#### 4. Security (Article 6, VII)
✅ **Compliant (MVP):**
- Database access controls
- Secure storage
- No public exposure of raw data
- HTTPS for all web traffic (Phase 2+)

⏳ **Enhanced (Phase 2):**
- Encryption at rest
- Access logs
- Penetration testing

#### 5. Quality & Accuracy (Article 6, V)
✅ **Compliant:**
- >85% accuracy validation
- Confidence thresholds
- Manual review process
- Correction mechanism

#### 6. Right to Access (Article 18, I)
⏳ **Phase 2 Required:**
- Lawyers can request their data
- Provide rating details and case history
- Response within 15 days

#### 7. Right to Correction (Article 18, III)
⏳ **Phase 2 Required:**
- Dispute mechanism for incorrect data
- Manual review process
- Corrections applied and logged

#### 8. Right to Deletion (Article 18, VI)
⚠️ **Complex - Not Full Deletion:**
- Cannot delete case outcomes (public transparency)
- Can anonymize lawyer identity
- Balance: privacy vs. public interest
- **Solution:** Anonymize but preserve statistics

**Implementation (Phase 2):**
```
Request deletion → Verify lawyer identity → Anonymize name/OAB →
Preserve anonymized rating for statistical integrity
```

#### 9. Data Processing Agreement
✅ **Not Required:**
- No third-party processors
- All processing in-house
- Internet Archive is data storage only (public data)

#### 10. Data Protection Officer (DPO)
⏳ **Phase 3:**
- Required if processing at scale
- Appoint DPO when >100K lawyers or >1M monthly users

### LGPD Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Lawyer privacy complaints | Medium | Low | Public data + legitimate interest |
| ANPD enforcement action | Low | Very Low | Proactive compliance |
| Data breach | Medium | Low | Security best practices |
| Inaccurate ratings | High | Medium | Validation + dispute process |
| Right to deletion conflicts | Medium | Medium | Anonymization approach |

**Overall Risk:** Low to Medium (manageable with proper controls)

---

## ⚖️ OAB (Ordem dos Advogados do Brasil)

The Brazilian Bar Association regulates lawyer conduct and ethics.

### OAB Code of Ethics Considerations

#### Article 28: Prohibition of Unfair Competition
> "Lawyers cannot use means that characterize unfair competition"

**Risk:** Could OAB view performance ratings as "unfair competition"?

**Mitigation:**
- Ratings are objective, not subjective
- Based on public court data
- All lawyers rated equally (no favoritism)
- Methodology is transparent

**Precedent:** Similar to doctor/hospital ratings (common in healthcare)

#### Article 31: Professional Advertising Rules
> "Lawyer advertising must be informative, discreet, and truthful"

**Impact:** CausaGanha is NOT lawyer advertising
- We don't represent lawyers
- Lawyers don't pay us
- We analyze public data independently

**Conclusion:** OAB advertising rules don't apply to us

#### Article 34: Confidentiality
> "Lawyers must maintain client confidentiality"

✅ **Compliant:**
- We only use public court decisions
- No access to privileged communications
- Case details are anonymized

### OAB Engagement Strategy

**Phase 1 (MVP):** Stealth - Don't engage yet
- Build product quietly
- Prove accuracy and methodology
- Gather data for credibility

**Phase 2 (Beta):** Inform
- Send letter to OAB leadership
- Explain mission (transparency, consumer protection)
- Invite dialogue
- Offer to address concerns

**Phase 3 (Launch):** Partner (if possible)
- Propose OAB collaboration on data validation
- Offer to incorporate OAB feedback
- Position as tool for lawyer quality improvement

**Worst Case:** OAB opposition
- Legal opinion: We have right to analyze public data
- Public interest argument
- Media support (transparency advocates)

---

## 📄 Court Data Usage

### PJe API Terms of Service

**Key Terms:**
1. Data is public and accessible to all
2. Must not overload court systems
3. Respect for judicial proceedings

**Compliance:**
✅ Rate limiting (respect API limits)
✅ Reasonable use (daily collection, not scraping)
✅ Proper attribution (cite tribunal sources)

### Risk: API Access Revoked

**Likelihood:** Low (public data mandate)
**Impact:** High (business critical)

**Mitigation:**
1. Maintain good relationships with courts
2. Legal right to public data access (transparency laws)
3. Diversify data sources (multiple tribunals)
4. Fallback: Manual collection if needed

---

## 🌐 Internet Archive Terms

### Internet Archive Collection Policy

**Terms:**
- Content must be public domain or legally uploadable
- Proper metadata and attribution
- No copyrighted material without permission

✅ **Compliant:**
- Court decisions are public documents
- Metadata includes tribunal, case number, date
- Attribution to original source (PJe)

### Risk: Archive Removal Requests

**Scenario:** Court or lawyer requests PDF removal from archive.org

**Response:**
1. Verify request legitimacy
2. If court-ordered removal: Comply
3. If lawyer request: Explain public data justification
4. Escalate to Internet Archive legal team if needed

**Impact:** Minimal (PDFs remain on court websites, archive is backup)

---

## 🔒 Data Security Requirements

### Minimum Security Standards (MVP)

**Infrastructure:**
- ✅ GitHub Secrets for API keys
- ✅ Environment variables (no hardcoded secrets)
- ✅ Private GitHub repository
- ✅ Database file permissions (read/write only by process)

**Code:**
- ✅ Input validation (Pydantic)
- ✅ SQL injection prevention (parameterized queries via Ibis)
- ✅ No eval() or exec() of user input

**Operations:**
- ✅ Daily database backups
- ✅ Logs do not contain secrets
- ✅ Error messages don't expose internals

### Enhanced Security (Phase 2+)

**Infrastructure:**
- HTTPS only (TLS 1.3)
- Database encryption at rest
- API authentication (API keys)
- Rate limiting per key
- DDoS protection (Cloudflare)

**Code:**
- Dependency scanning (Dependabot)
- SAST (static analysis security testing)
- Regular security audits

**Operations:**
- Incident response plan
- Breach notification procedures (24-48 hours)
- Regular penetration testing

---

## 🚨 Incident Response Plan

### Severity Levels

**P0 - Critical:**
- Data breach (lawyer data exposed)
- Database corruption
- Extended system outage

**P1 - High:**
- API credentials leaked
- Significant inaccuracy discovered (>20% error rate)
- Legal threat from OAB or court

**P2 - Medium:**
- Individual lawyer dispute
- Pipeline failure
- Performance degradation

**P3 - Low:**
- Minor bugs
- Enhancement requests

### Response Procedures

**Data Breach (P0):**
1. **Immediate:** Shut down affected systems
2. **1 hour:** Assess scope (what data, how many lawyers)
3. **24 hours:** Notify affected lawyers via email
4. **48 hours:** Report to ANPD (if >1000 lawyers)
5. **1 week:** Public disclosure and remediation plan

**Inaccuracy Report (P1):**
1. **Immediate:** Flag affected lawyer ratings
2. **24 hours:** Manual review of disputed cases
3. **48 hours:** Correction if confirmed
4. **1 week:** Root cause analysis and prevention

**OAB Legal Threat (P1):**
1. **Immediate:** Engage legal counsel
2. **48 hours:** Respond with legal justification
3. **1 week:** Seek mediation or compromise
4. **Ongoing:** Escalate if necessary

---

## 📋 Compliance Checklist

### MVP Launch Requirements
- [x] LGPD legal basis documented (legitimate interest)
- [x] Data minimization implemented
- [x] Security baseline (secrets management)
- [ ] Privacy policy draft
- [ ] Terms of service draft
- [ ] Dispute submission form (email)

### Public Beta Requirements (Phase 2)
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Right to access workflow
- [ ] Right to correction workflow
- [ ] Right to deletion workflow (anonymization)
- [ ] ANPD notification procedures
- [ ] OAB engagement initiated

### Public Launch Requirements (Phase 3)
- [ ] Legal counsel consultation (LGPD compliance audit)
- [ ] Data Protection Impact Assessment (DPIA)
- [ ] Security audit/penetration test
- [ ] DPO appointed (if required)
- [ ] Incident response plan tested

---

## 📖 Legal Opinions Required

### Before MVP Launch
- ✅ Informal legal research on LGPD applicability
- ⏳ Review by legal advisor ($2,000 budget)

### Before Public Beta
- ⏳ Formal legal opinion on LGPD compliance ($5,000)
- ⏳ OAB Code of Ethics review ($2,000)

### Before Public Launch
- ⏳ Full legal compliance audit ($10,000)
- ⏳ Ongoing legal counsel retainer ($1,000/month)

---

## 🎯 Compliance Success Metrics

**MVP:**
- Zero LGPD complaints
- Zero OAB complaints
- Zero court API access revocations

**Public Beta:**
- <5 lawyer dispute requests/month
- 100% dispute response within 48 hours
- Zero data breaches

**Public Launch:**
- <1% user complaints
- Zero regulatory enforcement actions
- Positive OAB relationship (neutral minimum)

---

## 📞 Key Contacts

**Legal Counsel:** TBD (engage before Public Beta)
**ANPD (Data Protection Authority):** https://www.gov.br/anpd
**OAB:** https://www.oab.org.br
**Internet Archive:** info@archive.org

---

**Last Updated:** 2025-01-19
**Next Review:** Before Public Beta (Month 7)
**Legal Disclaimer:** This document is for internal planning. Consult qualified legal counsel before making compliance decisions.
