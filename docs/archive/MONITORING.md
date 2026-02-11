# Backfill Health Monitoring System

Automated monitoring and Telegram alerting for causaganha backfill progress.

## Quick Start

### Run Health Check
```bash
cd /path/to/causaganha
python3 scripts/monitoring/check_backfill_health.py
```

### Test Alert (Dry Run)
```bash
python3 scripts/monitoring/check_backfill_health.py --dry-run --stale-hours 1
```

### OpenClaw Agent Integration
```bash
# From agent heartbeat
python3 scripts/monitoring/check_and_send_alert.py
# If output contains "SEND_TELEGRAM_ALERT", extract message and send via message tool
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Backfill Pipeline                          │
│  (GitHub Actions every 20 min)                               │
│  └─> Updates backfill-progress.json on Internet Archive     │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Health Monitoring (every 15-30 min)             │
│  check_backfill_health.py                                    │
│  • Fetches progress from Internet Archive                   │
│  • Detects stale/stuck conditions                           │
│  • Creates alert marker if issues found                     │
│  • Respects cooldown (max 1 alert per 6h per type)         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           OpenClaw Agent (heartbeat checks)                  │
│  check_and_send_alert.py                                     │
│  • Reads alert marker                                        │
│  • Sends Telegram via message tool                          │
│  • Removes marker after sending                             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Franklin (Telegram)
```

## Alert Conditions

### 1. Stale Progress (WARNING)
**Trigger:** No updates for >6 hours (configurable)
**Exit code:** 1
**Cooldown:** 6 hours

**Example:**
```
⚠️ BACKFILL STALE: No updates in 8.5h (progress: 2.09%)
```

### 2. Stuck Backfill (CRITICAL)
**Trigger:** Progress <0.1% AND no updates for >12 hours
**Exit code:** 2
**Cooldown:** 6 hours

**Example:**
```
🚨 BACKFILL STUCK: No progress in 15.2h (progress: 0.05%)
```

### 3. High Error Rate (CRITICAL)
**Trigger:** Error rate >50% sustained (future implementation)
**Exit code:** 2
**Cooldown:** 6 hours

## Files

```
scripts/monitoring/
├── check_backfill_health.py      # Core monitoring logic
├── check_and_send_alert.py       # OpenClaw agent integration
├── send_pending_alerts.py        # Alternative alert sender
├── monitor_and_alert.sh          # Wrapper script
├── README.md                     # Detailed documentation
├── .alert_history.json           # Alert throttling state (git-ignored)
└── .pending_alert.json           # Pending alert marker (git-ignored)
```

## Configuration

### Default Thresholds
```python
DEFAULT_STALE_HOURS = 6              # Alert if no progress >6h
DEFAULT_ERROR_THRESHOLD_PCT = 50.0   # Alert if errors >50%
DEFAULT_ALERT_COOLDOWN_HOURS = 6     # Max 1 alert per 6h per type
```

### Override via CLI
```bash
# Custom thresholds
python3 scripts/monitoring/check_backfill_health.py \
  --stale-hours 12 \
  --error-threshold 75 \
  --cooldown-hours 3

# Force send (bypass cooldown)
python3 scripts/monitoring/check_backfill_health.py --force
```

## Integration Examples

### OpenClaw Heartbeat
Add to `HEARTBEAT.md`:
```markdown
### ✅ Check Always (every heartbeat)
- Backfill health monitoring:
  ```bash
  cd /home/franklin/.openclaw/workspace/causaganha
  result=$(python3 scripts/monitoring/check_and_send_alert.py)
  if echo "$result" | grep -q "SEND_TELEGRAM_ALERT"; then
    # Extract message and send via message tool
    # message tool --channel telegram --target "+556984186712" --message "..."
  fi
  ```
```

### Standalone Cron Job
```cron
# Check every 15 minutes
*/15 * * * * cd /path/to/causaganha && python3 scripts/monitoring/check_backfill_health.py >> /var/log/causaganha/monitoring.log 2>&1
```

### GitHub Actions Workflow
Create `.github/workflows/monitoring.yml`:
```yaml
name: Backfill Monitoring

on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check backfill health
        run: python3 scripts/monitoring/check_backfill_health.py
        continue-on-error: true
      
      - name: Send Telegram alert
        if: hashFiles('scripts/monitoring/.pending_alert.json')
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: |
          # Send alert via Telegram API or OpenClaw
          python3 scripts/monitoring/send_telegram_alert.py
```

## Testing

### 1. Dry Run (No Alerts Sent)
```bash
# Test with current thresholds
python3 scripts/monitoring/check_backfill_health.py --dry-run

# Test with lower threshold to trigger alert
python3 scripts/monitoring/check_backfill_health.py --dry-run --stale-hours 1
```

### 2. Force Alert (Bypass Cooldown)
```bash
# Force send alert for testing
python3 scripts/monitoring/check_backfill_health.py --force --dry-run
```

### 3. Test Alert Throttling
```bash
# First run: should create alert
python3 scripts/monitoring/check_backfill_health.py --force --stale-hours 1

# Second run: should be throttled
python3 scripts/monitoring/check_backfill_health.py --stale-hours 1

# Check history
cat scripts/monitoring/.alert_history.json
```

### 4. Test OpenClaw Integration
```bash
# Simulate alert condition
cd /path/to/causaganha
python3 scripts/monitoring/check_and_send_alert.py --stale-hours 1

# Should output "SEND_TELEGRAM_ALERT" with message content
```

## Troubleshooting

### No Alerts Sent

**Possible causes:**
1. Alert cooldown active (check `.alert_history.json`)
2. Thresholds not met (backfill is actually healthy)
3. Network error fetching progress from Internet Archive

**Solutions:**
```bash
# Check alert history
cat scripts/monitoring/.alert_history.json

# Force send to bypass cooldown
python3 scripts/monitoring/check_backfill_health.py --force

# Test with lower threshold
python3 scripts/monitoring/check_backfill_health.py --stale-hours 1 --dry-run
```

### False Positives

**Possible causes:**
1. Thresholds too aggressive
2. Expected maintenance window
3. Temporary Internet Archive API issues

**Solutions:**
```bash
# Increase threshold
python3 scripts/monitoring/check_backfill_health.py --stale-hours 12

# Clear alert history to reset cooldown
rm scripts/monitoring/.alert_history.json
```

### Alert Marker Not Consumed

**Possible causes:**
1. OpenClaw agent not checking for alerts
2. Error sending Telegram message
3. Marker file permissions issue

**Solutions:**
```bash
# Check for pending alerts
ls -la scripts/monitoring/.pending_alert.json

# Manually inspect alert
cat scripts/monitoring/.pending_alert.json

# Remove stale marker
rm scripts/monitoring/.pending_alert.json
```

## Exit Codes

The monitoring script returns standard exit codes for integration with monitoring systems:

- `0`: **OK** - Backfill progressing normally
- `1`: **WARNING** - Minor issues detected (stale progress)
- `2`: **CRITICAL** - Backfill stuck or failing
- `3`: **UNKNOWN** - Cannot determine status (future use)

Example integration with monitoring tools:
```bash
python3 scripts/monitoring/check_backfill_health.py
case $? in
  0) echo "OK" ;;
  1) echo "WARNING" ;;
  2) echo "CRITICAL" ;;
  *) echo "UNKNOWN" ;;
esac
```

## Future Improvements

- [ ] GitHub Actions API integration for pipeline error tracking
- [ ] Tribunal-level health monitoring (detect specific tribunal failures)
- [ ] Prometheus metrics export
- [ ] Email alerting (in addition to Telegram)
- [ ] Alert aggregation (daily digest mode)
- [ ] Grafana dashboard integration
- [ ] Slack/Discord webhook support

## References

- [Main README](../README.md)
- [Monitoring Scripts README](../scripts/monitoring/README.md)
- [GitHub Actions Workflow](../.github/workflows/pipeline.yml)
- [Internet Archive Catalog](https://archive.org/download/causaganha-catalog/)

## Credits

**Implementation:** Funes (OpenClaw subagent)  
**Requested by:** Franklin  
**Date:** 2026-02-05  
**Priority:** High (prevents silent failures during backfill)
