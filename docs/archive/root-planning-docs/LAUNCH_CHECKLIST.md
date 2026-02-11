# CausaGanha Launch Checklist

## Pre-Launch Setup

### Domain & Hosting
- [ ] Register domain: causaganha.com.br
- [ ] Configure DNS to point to GitHub Pages (or custom hosting)
- [ ] Set up SSL certificate (automatic with GitHub Pages)
- [ ] Test landing page loads correctly

### Waitlist Backend (Cloudflare Workers)
```bash
# 1. Install Wrangler
npm install -g wrangler

# 2. Login to Cloudflare
wrangler login

# 3. Create KV namespace
cd landing
wrangler kv:namespace create "WAITLIST"

# 4. Update wrangler.toml with the namespace ID returned

# 5. Set admin token
wrangler secret put ADMIN_TOKEN
# Enter a secure random string

# 6. Deploy
wrangler deploy

# 7. Update landing page WAITLIST_API URL
```

### Analytics
- [ ] Create Google Analytics 4 property
- [ ] Add GA4 tracking code to landing page
- [ ] Set up conversion events (waitlist_signup)
- [ ] Create Google Search Console property
- [ ] Submit sitemap

### Email Marketing
- [ ] Set up email service (Resend, SendGrid, or Mailchimp)
- [ ] Create welcome email template
- [ ] Set up automation for new signups
- [ ] Test email delivery

### Legal
- [ ] Create Terms of Service page
- [ ] Create Privacy Policy page (LGPD compliant)
- [ ] Add cookie consent banner (if using cookies)

---

## Launch Day

### Technical
- [ ] Verify landing page is live
- [ ] Test waitlist form submission
- [ ] Check mobile responsiveness
- [ ] Verify analytics is tracking

### Marketing
- [ ] Post announcement on LinkedIn
- [ ] Share in relevant groups/communities
- [ ] Send email to personal network
- [ ] Update personal LinkedIn/Twitter bio with link

### Monitoring
- [ ] Monitor waitlist signups in real-time
- [ ] Check for errors in Cloudflare dashboard
- [ ] Respond to any support requests

---

## Post-Launch (Week 1)

### Metrics to Track
| Metric | Goal | Actual |
|--------|------|--------|
| Landing page visits | 500 | |
| Waitlist signups | 100 | |
| Conversion rate | 20% | |
| Bounce rate | < 60% | |

### Tasks
- [ ] Analyze traffic sources
- [ ] Review user feedback
- [ ] Publish first blog post
- [ ] Start LinkedIn content cadence
- [ ] Send first newsletter to waitlist

---

## Commands Reference

### Deploy Landing Page
```bash
# Landing page auto-deploys via GitHub Actions on push to main
# Or manually trigger the workflow in GitHub Actions
```

### Check Waitlist Stats
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  https://causaganha-waitlist.YOUR_SUBDOMAIN.workers.dev/stats
```

### Export Waitlist Emails
```bash
curl -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  https://causaganha-waitlist.YOUR_SUBDOMAIN.workers.dev/export
```

### Local Development
```bash
# Serve landing page locally
cd landing
python -m http.server 8000
# Visit http://localhost:8000
```

---

## Key URLs

| Resource | URL |
|----------|-----|
| Landing Page | https://causaganha.com.br |
| GitHub Repo | https://github.com/franklinbaldo/causaganha |
| Cloudflare Dashboard | https://dash.cloudflare.com |
| Google Analytics | https://analytics.google.com |
| Google Search Console | https://search.google.com/search-console |

---

## Emergency Contacts

- Domain registrar support
- Cloudflare support
- GitHub support

---

## Notes

_Use this space to track any issues or learnings during launch_

---

*Checklist Version: 1.0*
*Last Updated: January 2026*
