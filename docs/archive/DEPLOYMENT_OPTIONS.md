# CausaGanha Deployment Options Comparison

Complete guide to choosing the best deployment option for your continuous embedding generation needs.

## Quick Comparison Table

| Option | Monthly Cost | Throughput | Setup | Best For |
|--------|-------------|------------|-------|----------|
| **Old Android Phone** 📱 | **$6-7** | 4-14k/day | Medium | **RECOMMENDED** for private repos |
| **GitHub Actions (public)** ☁️ | **$5** | 18k/day | Easy | **BEST** if can make repo public |
| Laptop (24/7) 💻 | $10-15 | 18k/day | Easy | Home server |
| Self-hosted PC 🖥️ | $15-20 | 36k+/day | Easy | Large tribunals |
| GitHub Actions (private) | $156 | 18k/day | Easy | ❌ Too expensive |
| Cloud Run | $27 | 18k/day | Hard | Professional setups |

---

## Option 1: Old Android Phone ⭐ **BEST FOR MOST USERS**

**Setup**: Termux + Python + continuous service

### Costs

```
Hardware: $0 (reuse old phone)
Electricity: ~$1-2/month (5-10W × 24h × 30 days × $0.12/kWh)
Jina API: ~$5/month (540k decisions)
Total: ~$6-7/month
```

### Performance

```
Typical mid-range phone (3 GB RAM):
├─ Throughput: 5-10 decisions/minute
├─ Daily capacity: 7,000-14,000 decisions
├─ Concurrent requests: 5-10
└─ Covers TJRO (2,000/day) with 3-7x headroom ✅
```

### Pros

✅ **Cheapest option** (~$6/month total)
✅ **Built-in UPS** (battery backup during power outages)
✅ **Always-on design** (phones are built for 24/7)
✅ **Ultra-low power** (5-10W vs 50-100W for laptop)
✅ **Silent operation** (no fans)
✅ **Small footprint** (fits anywhere)
✅ **Private repo** (no need to make public)

### Cons

⚠️ Medium setup complexity (Termux)
⚠️ Phone-specific issues (overheating, battery optimization)
⚠️ Limited resources (2-4 GB RAM typical)
⚠️ May require monitoring

### When to Use

- ✅ Small to medium tribunals (<10k decisions/day)
- ✅ Want to keep repository private
- ✅ Have an old Android phone lying around
- ✅ Budget-conscious deployment
- ✅ Home/personal use

### Documentation

See [ANDROID_DEPLOYMENT.md](./ANDROID_DEPLOYMENT.md) for complete setup guide.

---

## Option 2: GitHub Actions (Public Repo) ⭐ **BEST IF CAN MAKE PUBLIC**

**Setup**: Enable workflow, make repo public

### Costs

```
GitHub Actions: $0/month (unlimited minutes for public repos)
Jina API: ~$5/month (540k decisions)
Total: ~$5/month
```

### Performance

```
Runs every 20 minutes (72/day):
├─ Throughput: 10-20 decisions/minute per run
├─ Daily capacity: 18,000 decisions
├─ Runtime: 45-55 minutes per run
└─ Covers medium tribunals (10k/day) with 1.8x headroom ✅
```

### Pros

✅ **Lowest total cost** ($5/month)
✅ **Unlimited compute** (public repos)
✅ **Zero maintenance** (managed service)
✅ **Easy setup** (just enable workflow)
✅ **High throughput** (18k/day)
✅ **Automatic restarts** (if failures)
✅ **Professional infrastructure** (GitHub's servers)

### Cons

⚠️ **Requires public repository**
⚠️ 6-hour timeout per run (not an issue for hourly runs)
⚠️ <1 hour latency (hourly runs)

### When to Use

- ✅ **ALWAYS** if you can make the repo public
- ✅ Medium to large tribunals (up to 15k/day)
- ✅ Want zero maintenance
- ✅ Don't mind public code/data
- ✅ Professional deployment

### Documentation

See [CONTINUOUS_EMBEDDINGS.md](./CONTINUOUS_EMBEDDINGS.md) for complete guide.

---

## Option 3: Laptop (24/7)

**Setup**: Run `laptop_service.py` with screen/systemd

### Costs

```
Electricity: ~$5-10/month (50-100W)
Jina API: ~$5/month
Total: ~$10-15/month
```

### Performance

```
Modern laptop (8+ GB RAM):
├─ Throughput: 10-20 decisions/minute
├─ Daily capacity: 14,000-28,000 decisions
└─ Covers medium to large tribunals ✅
```

### Pros

✅ Simple setup
✅ High performance
✅ Full control
✅ Private repo
✅ Can handle large workloads

### Cons

⚠️ Higher power cost ($5-10/month)
⚠️ Laptop must stay on 24/7
⚠️ Fan noise (depending on model)
⚠️ Larger footprint
⚠️ No built-in UPS (unless laptop battery)

### When to Use

- ✅ Have spare laptop
- ✅ Medium to large tribunals
- ✅ Want simple setup
- ✅ Private repo

---

## Option 4: Self-hosted PC/Server

**Setup**: Same as laptop, but dedicated hardware

### Costs

```
Electricity: ~$10-20/month (100-200W)
Jina API: ~$5/month
Total: ~$15-25/month
```

### Performance

```
Desktop PC (16+ GB RAM):
├─ Throughput: 20-40 decisions/minute
├─ Daily capacity: 30,000-60,000 decisions
└─ Covers large tribunals (TJSP, TJRJ) ✅
```

### Pros

✅ Highest performance
✅ Full control
✅ Can scale indefinitely
✅ Private repo

### Cons

⚠️ Highest electricity cost
⚠️ Noisy (fans)
⚠️ Large footprint
⚠️ Requires dedicated hardware

### When to Use

- ✅ Large tribunals (20k+ decisions/day)
- ✅ Have dedicated server
- ✅ Need maximum performance
- ✅ Private repo

---

## Option 5: GitHub Actions (Private Repo) ❌ **NOT RECOMMENDED**

**Setup**: Same as public, but private repo

### Costs

```
GitHub Actions: ~$156/month (21,600 min - 2,000 free)
Jina API: ~$5/month
Total: ~$161/month ⚠️
```

### Performance

Same as public repo (18k/day).

### Verdict

❌ **Too expensive** - Use phone/laptop instead for private repos

---

## Option 6: Google Cloud Run

**Setup**: Docker container, Cloud Run deployment

### Costs

```
Cloud Run: ~$22/month (continuous job)
Jina API: ~$5/month
Total: ~$27/month
```

### Performance

Similar to laptop (14-28k/day).

### Pros

✅ Professional infrastructure
✅ Auto-scaling
✅ Zero maintenance
✅ Private repo

### Cons

⚠️ More expensive than phone/laptop
⚠️ Complex setup (Docker, GCP)
⚠️ Requires credit card

### When to Use

- ✅ Professional/commercial deployments
- ✅ Need auto-scaling
- ✅ Want managed service
- ✅ Private repo + budget for cloud

---

## Decision Tree

### Step 1: Can you make the repository public?

**YES** → Use **GitHub Actions (public)** - $5/month, easiest, unlimited ✅

**NO** → Continue to Step 2

### Step 2: What's your daily decision volume?

**<10,000/day** (small tribunals like TJRO):
- → Use **Old Android Phone** - $6/month, reliable ⭐

**10,000-20,000/day** (medium tribunals):
- → Use **Laptop 24/7** - $10-15/month, powerful

**20,000+/day** (large tribunals like TJSP):
- → Use **Self-hosted PC** - $15-25/month, maximum performance
- → Or **multiple Android phones** in parallel

### Step 3: Budget considerations

**Minimizing cost** (<$10/month):
- → **Android Phone** ($6-7/month) ⭐
- → Or make repo public for GitHub Actions ($5/month)

**Balancing cost and performance** ($10-20/month):
- → **Laptop** ($10-15/month)

**Professional/commercial** (budget not primary concern):
- → **GitHub Actions (public)** if possible ($5/month)
- → **Cloud Run** if must stay private ($27/month)

---

## Recommendations by Use Case

### Personal/Academic Research

**Recommended**: Old Android Phone or GitHub Actions (public)
- Low cost ($5-7/month)
- Covers small to medium tribunals
- Simple to maintain

### Startup/Small Business (Private Data)

**Recommended**: Old Android Phone or Laptop
- Keep data private
- Low cost ($6-15/month)
- Reliable for production use

### Professional/Enterprise (High Volume)

**Recommended**: GitHub Actions (public) or Self-hosted PC
- If can be public: GitHub Actions ($5/month)
- If must be private: Self-hosted PC ($15-25/month)
- High throughput, professional infrastructure

### Large Tribunal Coverage (TJSP, TJRJ)

**Recommended**: Self-hosted PC or Multiple Phones
- 30k-60k+ decisions/day capacity
- Parallel processing
- Consider hybrid: GitHub Actions + Cloud Run for peaks

---

## Setup Difficulty Comparison

| Option | Setup Time | Technical Skill | Maintenance |
|--------|-----------|-----------------|-------------|
| **GitHub Actions** | 10 min | Easy | None |
| **Laptop** | 20 min | Easy | Low |
| **Android Phone** | 45 min | Medium | Medium |
| **Self-hosted PC** | 30 min | Easy | Low |
| **Cloud Run** | 2 hours | Hard | Low |

---

## Power Consumption Comparison

| Device | Power (W) | Daily (kWh) | Monthly ($) |
|--------|-----------|-------------|-------------|
| **Android Phone** | 5-10 | 0.12-0.24 | $1-2 |
| **Laptop (idle)** | 20-40 | 0.48-0.96 | $2-4 |
| **Laptop (active)** | 50-100 | 1.2-2.4 | $5-10 |
| **Desktop PC** | 100-200 | 2.4-4.8 | $10-20 |

*Assumes $0.12/kWh electricity rate*

---

## Final Recommendation

### 🥇 **Best Overall**: Old Android Phone

**Why**:
- Cheapest total cost ($6-7/month)
- Designed for 24/7 operation
- Built-in battery backup
- Silent, small, efficient
- Covers most use cases (up to 14k/day)

**Use unless**:
- You can make repo public → Use GitHub Actions instead ($5/month)
- You need >15k/day throughput → Use laptop or PC

### 🥈 **Best if Public Repo**: GitHub Actions

**Why**:
- Lowest cost ($5/month)
- Zero maintenance
- Professional infrastructure
- Highest throughput (18k/day)

### 🥉 **Best for Large Tribunals**: Self-hosted PC

**Why**:
- Maximum performance (30k-60k/day)
- Can scale indefinitely
- Full control

---

## Migration Path

Start small, scale up as needed:

```
1. MVP → Old Android Phone ($6/month)
         Test with TJRO (2k/day)

2. Scale → Add second phone or upgrade to laptop
         Cover medium tribunals (10k/day)

3. Production → Self-hosted PC or GitHub Actions
                Cover large tribunals (20k+/day)
```

---

## Support

For deployment help:
- Android setup: See [ANDROID_DEPLOYMENT.md](./ANDROID_DEPLOYMENT.md)
- GitHub Actions: See [CONTINUOUS_EMBEDDINGS.md](./CONTINUOUS_EMBEDDINGS.md)
- Laptop service: See [DAILY_EMBEDDINGS.md](./DAILY_EMBEDDINGS.md)
- Issues: https://github.com/franklinbaldo/causaganha/issues
