# Running CausaGanha on Android Phone (Termux)

This guide shows how to run the continuous embedding service on an **old Android phone** using Termux. This is one of the **best and cheapest** deployment options!

## Why Use an Old Android Phone?

✅ **Advantages**:
- **Always-on design**: Phones are built to run 24/7
- **Ultra-low power**: ~5-10W (vs 50-100W for laptop)
- **Built-in UPS**: Battery backup during power outages
- **Cheap electricity**: ~$1-2/month (vs $5-10 for laptop)
- **Silent operation**: No fans
- **Small footprint**: Fits anywhere
- **Free compute**: Uses device you already own
- **Private repo**: No need to make repository public

✅ **Cost Comparison**:
```
Android Phone:
├─ Electricity: ~$1-2/month (5-10W continuous)
├─ Jina API: ~$5/month
└─ Total: ~$6-7/month

vs

GitHub Actions (private): $156/month
Cloud Run: $27/month
Laptop: $15/month
```

## Requirements

- **Android phone** (Android 7.0+)
- **Storage**: 2-4 GB free space
- **RAM**: 2+ GB recommended
- **Internet**: WiFi connection
- **Power**: Keep plugged in

**Recommended**: Old flagship phones (Samsung Galaxy S7+, OnePlus 3+, Pixel 1+) work great!

## Setup Guide

### Step 1: Install Termux

1. **Download Termux** from F-Droid (NOT Google Play - outdated version):
   - Go to https://f-droid.org/packages/com.termux/
   - Or install F-Droid app first, then search "Termux"

2. **Install Termux**:
   - Open downloaded APK
   - Grant installation permissions
   - Open Termux app

### Step 2: Install Dependencies

```bash
# Update package manager
pkg update && pkg upgrade -y

# Install essential packages
pkg install -y \
    python \
    git \
    clang \
    rust \
    binutils \
    pkg-config \
    libffi \
    openssl

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Clone Repository

```bash
# Generate SSH key (if needed)
pkg install openssh
ssh-keygen -t ed25519 -C "your_email@example.com"

# Show public key (add to GitHub)
cat ~/.ssh/id_ed25519.pub

# Clone repository
cd ~
git clone git@github.com:franklinbaldo/causaganha.git
cd causaganha
```

### Step 4: Setup Python Environment

```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv sync --no-dev

# Install package
uv pip install -e .
```

### Step 5: Configure Environment

```bash
# Create .env file
nano .env

# Add your API keys:
JINA_API_KEY=your_jina_key_here
GOOGLE_API_KEY=your_google_key_here  # Optional fallback
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### Step 6: Test Service

```bash
# Test with small batch
uv run python scripts/laptop_service.py

# Should see:
# ============================================================
# CausaGanha Embedding Service (Laptop)
# ============================================================
#   Batch size: 50 decisions
#   Concurrency: 10 parallel requests
#   ...
```

Press `Ctrl+C` to stop after verifying it works.

### Step 7: Run as Background Service

#### Option A: Using `screen` (Simple)

```bash
# Install screen
pkg install screen

# Start screen session
screen -S embeddings

# Run service
source .venv/bin/activate
uv run python scripts/laptop_service.py

# Detach: Press Ctrl+A, then D
# Service continues running in background!

# Re-attach to view logs
screen -r embeddings

# Kill session
screen -X -S embeddings quit
```

#### Option B: Using Termux:Boot (Auto-start on boot)

```bash
# Install Termux:Boot from F-Droid
# https://f-droid.org/packages/com.termux.boot/

# Create startup script
mkdir -p ~/.termux/boot
nano ~/.termux/boot/start-embeddings.sh

# Add this content:
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock  # Prevent phone from sleeping
cd ~/causaganha
source .venv/bin/activate
uv run python scripts/laptop_service.py >> ~/embeddings.log 2>&1

# Make executable
chmod +x ~/.termux/boot/start-embeddings.sh

# Reboot phone - service will auto-start!
```

## Monitoring

### View Logs

```bash
# If using screen
screen -r embeddings

# If using Termux:Boot
tail -f ~/embeddings.log

# Check last 100 lines
tail -n 100 ~/embeddings.log

# Search for errors
grep -i error ~/embeddings.log
```

### Check Status

```bash
# Check if process is running
ps aux | grep laptop_service

# Check resource usage
top

# Check network usage
termux-battery-status
```

## Optimization

### Reduce Battery Drain

```bash
# In environment settings (adjust in .bashrc or service script)
export BATCH_SIZE=25           # Smaller batches (default: 50)
export MAX_CONCURRENCY=5       # Less parallel requests (default: 10)
export IDLE_SLEEP_SECONDS=600  # Longer idle sleep (default: 300)
```

### Keep Phone Awake

```bash
# Install Termux:API
pkg install termux-api

# Acquire wake lock (prevents sleep)
termux-wake-lock
```

### Prevent Overheating

- Remove phone case
- Place phone in well-ventilated area
- Consider small USB fan if overheating occurs
- Reduce `MAX_CONCURRENCY` to 5-8 if phone gets hot

### Disable Battery Optimization

1. Go to Android Settings
2. Apps → Termux
3. Battery → Unrestricted
4. This prevents Android from killing Termux in background

## Troubleshooting

### Service Stops Running

**Cause**: Android killed Termux to save battery

**Solutions**:
1. Disable battery optimization (see above)
2. Use `termux-wake-lock`
3. Keep Termux in foreground (swipe up from bottom, pin Termux)
4. Use Termux:Boot to auto-restart

### Phone Gets Too Hot

**Solutions**:
1. Reduce `MAX_CONCURRENCY` from 10 → 5
2. Reduce `BATCH_SIZE` from 50 → 25
3. Add longer sleep between batches
4. Place phone in cooler location
5. Remove phone case

### Out of Storage

**Solutions**:
1. Clear old logs: `rm ~/embeddings.log`
2. Clear cache: `pkg clean`
3. Use external SD card (if available)

### WiFi Disconnects

**Solution**: Set WiFi to "Always on" in developer settings
1. Settings → About Phone → Tap "Build Number" 7 times
2. Settings → Developer Options → WiFi → "Stay awake when plugged in"

## Performance Expectations

**Typical Android Phone** (Mid-range, ~3 GB RAM):
```
Throughput: ~5-10 decisions/minute
Daily capacity: ~7,000-14,000 decisions
Power usage: 5-10W (0.12-0.24 kWh/day)
Monthly cost: $1-2 electricity + $5 API = $6-7 total
```

**Older Phone** (Budget, ~2 GB RAM):
```
Throughput: ~3-5 decisions/minute
Daily capacity: ~4,000-7,000 decisions
Power usage: 3-8W
Monthly cost: $1 electricity + $5 API = $6 total
```

## Maintenance

### Weekly Checklist

- [ ] Check if service is still running
- [ ] Review logs for errors
- [ ] Check phone temperature (should be warm, not hot)
- [ ] Verify decisions are being processed

### Monthly Checklist

- [ ] Update repository: `git pull`
- [ ] Update dependencies: `uv sync`
- [ ] Check phone storage: `df -h`
- [ ] Clean old logs: `rm ~/embeddings.log`
- [ ] Restart service: `screen -X -S embeddings quit && screen -S embeddings -dm bash -c 'cd ~/causaganha && source .venv/bin/activate && uv run python scripts/laptop_service.py'`

## Advanced Tips

### Multiple Phones

Run multiple phones for higher throughput:
```bash
# Phone 1: Process decisions 1-1000
export BATCH_OFFSET=0

# Phone 2: Process decisions 1001-2000
export BATCH_OFFSET=1000

# Modify query in script to use OFFSET
```

### Remote Access

Access logs from anywhere:
```bash
# Install SSH server
pkg install openssh
sshd

# Find phone IP
ifconfig wlan0 | grep inet

# Connect from PC
ssh -p 8022 u0_a123@192.168.1.XXX
```

### Auto-recovery

Add auto-restart on crash:
```bash
#!/bin/bash
while true; do
    cd ~/causaganha
    source .venv/bin/activate
    uv run python scripts/laptop_service.py
    echo "Service crashed, restarting in 10 seconds..."
    sleep 10
done
```

## Comparison: All Deployment Options

| Option | Monthly Cost | Setup | Pros | Cons |
|--------|-------------|-------|------|------|
| **Android Phone** | $6-7 | Medium | Cheap, reliable, UPS | Phone-specific issues |
| **Laptop (Linux)** | $10-15 | Easy | Simple, powerful | Higher power cost |
| **GitHub Actions (public)** | $5 | Easy | Zero compute cost | Repo must be public |
| **GitHub Actions (private)** | $156 | Easy | Simple | Very expensive |
| **Cloud Run** | $27 | Hard | Professional | Most expensive |
| **Self-hosted PC** | $15-20 | Easy | Full control | Noisy, large |

## Recommended Phone Models

**Best Options** (Good performance, widely available):
- Samsung Galaxy S7/S8/S9
- OnePlus 3/3T/5/6
- Google Pixel 1/2/3
- Xiaomi Redmi Note 8+
- Motorola Moto G6+

**Avoid**:
- Phones with <2 GB RAM
- Phones with broken battery (must stay plugged in anyway, but safety risk)
- Phones with known overheating issues

## Conclusion

Using an old Android phone is **one of the best ways** to run CausaGanha's embedding service:

✅ **Cheapest option** (~$6-7/month total)
✅ **Reliable** (built for 24/7 operation)
✅ **Silent** (no fans)
✅ **Portable** (fits anywhere)
✅ **Built-in UPS** (battery backup)
✅ **Private repo** (no need to make public)

Perfect for:
- Small to medium tribunals
- Private repositories
- Low-budget deployments
- Home/personal use

For large tribunals (20,000+ decisions/day), consider using multiple phones or upgrading to laptop/cloud.
