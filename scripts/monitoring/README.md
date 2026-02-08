# Backfill Health Monitoring

Automated monitoring and alerting for causaganha backfill progress.

## Overview

The monitoring system checks backfill health and sends Telegram alerts when issues are detected:
- **Stale progress**: No updates for >6 hours (configurable)
- **Stuck backfill**: Progress <0.1% and no updates for >12 hours
- **High error rate**: >50% failure rate (future implementation)

## Components

### 1. Health Check Script
`check_backfill_health.py` - Core monitoring logic

**Features:**
- Fetches backfill progress from Internet Archive catalog
- Detects stale/stuck conditions
- Creates alert markers when issues found
- Implements alert throttling (max 1 alert per 6h per issue type)

**Usage:**
```bash
# Run health check (exits 0=ok, 1=warning, 2=critical)
python scripts/monitoring/check_backfill_health.py

# Custom thresholds
python scripts/monitoring/check_backfill_health.py --stale-hours 12 --error-threshold 75

# Dry run (don't send alerts)
python scripts/monitoring/check_backfill_health.py --dry-run

# Force send alert (bypass cooldown)
python scripts/monitoring/check_backfill_health.py --force
```

**Exit Codes:**
- `0`: OK - Backfill progressing normally
- `1`: WARNING - Minor issues detected
- `2`: CRITICAL - Backfill stuck or failing

### 2. Alert Sender
`send_pending_alerts.py` - Sends alerts via Telegram

This script reads alert markers created by the health check and outputs the message in a format the OpenClaw agent can parse.

**Usage:**
```bash
# Check for pending alerts (called by OpenClaw agent)
python scripts/monitoring/send_pending_alerts.py
```

### 3. Wrapper Script
`monitor_and_alert.sh` - Combines health check + alert detection

**Usage:**
```bash
# Run monitoring (creates alert markers)
./scripts/monitoring/monitor_and_alert.sh

# Dry run
./scripts/monitoring/monitor_and_alert.sh --dry-run
```

## Alert Format

Telegram alerts include:
- **Status summary**: Progress %, item count, date range, age
- **Severity indicator**: 🚨 CRITICAL / ⚠️ WARNING
- **Next steps**: Actionable troubleshooting guidance
- **Quick links**: GitHub Actions, Dashboard

Example alert:
```
🔔 CausaGanha Backfill Alert

⚠️ BACKFILL STALE: No updates in 8.5h (progress: 2.09%)

Status:
• Progress: 2.09%
• Total items: 287
• Date range: 2026-01-09 → 2026-02-04
• Last update: 8.5h ago

Next Steps:
1. Check if scheduled runs are executing
2. Review recent workflow logs
3. Monitor for next update (expected every 15min)

🔗 GitHub Actions
🔗 Dashboard
```

## Alert Throttling

Prevents spam by limiting alerts to **max 1 per 6 hours per issue type**.

Alert types:
- `stale`: No progress detected
- `stuck`: Backfill completely stopped
- `error`: High error rate (future)

Alert history stored in `.alert_history.json` (git-ignored).

To bypass cooldown:
```bash
python scripts/monitoring/check_backfill_health.py --force
```

## Integration with OpenClaw Agent

The monitoring system integrates with OpenClaw's heartbeat system:

1. **Heartbeat runs monitoring**: Every 15-30 minutes
2. **Health check creates marker**: If issues detected
3. **Agent detects marker**: Reads pending alert
4. **Agent sends Telegram**: Uses `message` tool with channel="telegram"
5. **Marker removed**: After successful send

**In HEARTBEAT.md:**
```markdown
### ✅ Check Always (every heartbeat)
- Backfill health (scripts/monitoring/monitor_and_alert.sh)
- Check for pending alerts (send_pending_alerts.py)
```

## Cron Integration

For standalone monitoring (outside OpenClaw heartbeat):

```bash
# Add to crontab
*/15 * * * * cd /home/franklin/.openclaw/workspace/causaganha && ./scripts/monitoring/monitor_and_alert.sh >> /var/log/causaganha/monitoring.log 2>&1
```

Or create a systemd timer:
```bash
# Copy systemd files (future implementation)
sudo cp deployment/systemd/causaganha-monitoring.service /etc/systemd/system/
sudo cp deployment/systemd/causaganha-monitoring.timer /etc/systemd/system/
sudo systemctl enable --now causaganha-monitoring.timer
```

## Configuration

Default thresholds (can be overridden via CLI args):

```python
DEFAULT_STALE_HOURS = 6              # Alert if no progress >6h
DEFAULT_ERROR_THRESHOLD_PCT = 50.0   # Alert if errors >50%
DEFAULT_ALERT_COOLDOWN_HOURS = 6     # Max 1 alert per 6h per type
```

Environment variables (optional):
```bash
export TELEGRAM_TARGET="+556984186712"  # Alert recipient
```

## Testing

### 1. Dry Run Test
```bash
# Test monitoring without sending alerts
./scripts/monitoring/monitor_and_alert.sh --dry-run
```

### 2. Simulated Stuck Backfill
```bash
# Create fake old progress file
cat > /tmp/fake-progress.json << EOF
{
  "progress_pct": 0.5,
  "oldest_date": "2026-01-09",
  "newest_date": "2026-02-04",
  "total_items": 287,
  "last_updated": "2026-02-04T00:00:00+00:00"
}
EOF

# Modify script temporarily to read from /tmp
# (or wait for real staleness in production)
```

### 3. Force Alert Test
```bash
# Bypass cooldown and send test alert
python scripts/monitoring/check_backfill_health.py --force --dry-run
```

### 4. Alert Throttling Test
```bash
# First run: should create alert
python scripts/monitoring/check_backfill_health.py --force

# Second run: should be throttled (within 6h)
python scripts/monitoring/check_backfill_health.py

# Check alert history
cat scripts/monitoring/.alert_history.json
```

## Troubleshooting

### No alerts being sent
1. Check alert history: `cat scripts/monitoring/.alert_history.json`
2. Check cooldown period (6h default)
3. Verify backfill is actually stuck: `curl https://archive.org/download/causaganha-catalog/backfill-progress.json`
4. Run with `--force` to bypass cooldown

### Alert marker not being sent
1. Ensure OpenClaw agent has access to `message` tool
2. Check agent heartbeat is running
3. Verify marker exists: `ls scripts/monitoring/.pending_alert.json`
4. Manually send: Run `send_pending_alerts.py` and use output with message tool

### False positives
1. Increase stale threshold: `--stale-hours 12`
2. Review alert history patterns
3. Adjust thresholds in script if needed

## Future Improvements

- [ ] GitHub Actions API integration for error rate tracking
- [ ] Tribunal-level health tracking (detect specific tribunal failures)
- [ ] Prometheus metrics export for dashboard integration
- [ ] Email alerting (in addition to Telegram)
- [ ] Systemd timer for standalone deployment
- [ ] Alert aggregation (daily digest mode)

## Files

```
scripts/monitoring/
├── check_backfill_health.py    # Core health check logic
├── send_pending_alerts.py      # Alert sender (for agent)
├── monitor_and_alert.sh        # Wrapper script
├── README.md                   # This file
├── .alert_history.json         # Alert throttling state (git-ignored)
└── .pending_alert.json         # Pending alert marker (git-ignored)
```

## Credits

**Implementation:** Funes (OpenClaw subagent)  
**Requested by:** Franklin  
**Project:** causaganha backfill monitoring  
**Date:** 2026-02-05
