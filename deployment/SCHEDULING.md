# Scheduling Guide for CausaGanha Parquet Exports

This guide explains how to set up automated daily Parquet exports for CausaGanha.

## Overview

CausaGanha exports analyzed decisions to Parquet files daily at **02:00 UTC**. This timing is chosen to:
- Run after daily data collection and analysis completes (~00:00-01:00 UTC)
- Avoid peak Internet Archive upload hours
- Provide consistent timing across time zones

## Prerequisites

1. **CausaGanha installed** at `/opt/causaganha` (or adjust paths below)
2. **Virtual environment activated** with all dependencies
3. **Internet Archive credentials configured**:
   ```bash
   export IA_ACCESS_KEY="your_access_key"
   export IA_SECRET_KEY="your_secret_key"
   ```
4. **Sufficient disk space** for temporary Parquet files (~500MB per day)
5. **Network connectivity** to Internet Archive

## Option 1: Systemd Timer (Recommended for modern Linux)

Systemd timers provide better logging, resource management, and error handling than cron.

### Installation

1. **Copy service and timer files**:
   ```bash
   sudo cp deployment/systemd/causaganha-export.service /etc/systemd/system/
   sudo cp deployment/systemd/causaganha-export.timer /etc/systemd/system/
   ```

2. **Update paths in service file** (if not using `/opt/causaganha`):
   ```bash
   sudo nano /etc/systemd/system/causaganha-export.service
   # Update WorkingDirectory, ExecStart, ReadWritePaths
   ```

3. **Create causaganha user** (if it doesn't exist):
   ```bash
   sudo useradd -r -s /bin/false -d /opt/causaganha causaganha
   sudo chown -R causaganha:causaganha /opt/causaganha
   ```

4. **Reload systemd and enable timer**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable causaganha-export.timer
   sudo systemctl start causaganha-export.timer
   ```

### Management

**Check timer status**:
```bash
sudo systemctl status causaganha-export.timer
sudo systemctl list-timers causaganha-export.timer
```

**View logs**:
```bash
# Recent logs
sudo journalctl -u causaganha-export.service -n 50

# Follow logs in real-time
sudo journalctl -u causaganha-export.service -f

# Logs from today
sudo journalctl -u causaganha-export.service --since today

# Logs from specific date
sudo journalctl -u causaganha-export.service --since "2025-01-15"
```

**Manual execution** (for testing):
```bash
sudo systemctl start causaganha-export.service
```

**Stop/disable timer**:
```bash
sudo systemctl stop causaganha-export.timer
sudo systemctl disable causaganha-export.timer
```

### Monitoring

**Check last run**:
```bash
systemctl status causaganha-export.timer
```

**Next scheduled run**:
```bash
systemctl list-timers causaganha-export.timer --all
```

**Export success rate**:
```bash
sudo journalctl -u causaganha-export.service --since "7 days ago" | grep "daily_export_completed"
```

## Option 2: Cron (Alternative)

For systems without systemd or if you prefer cron.

### Installation

1. **Copy cron file**:
   ```bash
   sudo cp deployment/cron/causaganha-export.cron /etc/cron.d/causaganha-export
   sudo chmod 644 /etc/cron.d/causaganha-export
   ```

2. **Update paths and email** in `/etc/cron.d/causaganha-export`:
   ```bash
   sudo nano /etc/cron.d/causaganha-export
   # Update MAILTO, paths
   ```

3. **Create log directory**:
   ```bash
   sudo mkdir -p /var/log/causaganha
   sudo chown causaganha:causaganha /var/log/causaganha
   ```

### Alternative: User Crontab

For non-root installation:

```bash
crontab -e
```

Add this line:
```cron
0 2 * * * cd /home/user/causaganha && /home/user/causaganha/.venv/bin/python scripts/daily_export.py >> /home/user/causaganha/logs/export.log 2>&1
```

### Management

**View cron jobs**:
```bash
crontab -l
```

**Check logs**:
```bash
tail -f /var/log/causaganha/export.log
```

**Test manually**:
```bash
cd /opt/causaganha
.venv/bin/python scripts/daily_export.py
```

## Option 3: Docker/Kubernetes CronJob

For containerized deployments.

### Kubernetes CronJob

Create `k8s/cronjob-export.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: causaganha-export
spec:
  schedule: "0 2 * * *"  # 02:00 UTC daily
  timeZone: "UTC"
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 7
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: export
            image: causaganha:latest
            command:
            - python
            - scripts/daily_export.py
            env:
            - name: IA_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: causaganha-secrets
                  key: ia-access-key
            - name: IA_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: causaganha-secrets
                  key: ia-secret-key
            volumeMounts:
            - name: data
              mountPath: /app/data
          restartPolicy: OnFailure
          volumes:
          - name: data
            persistentVolumeClaim:
              claimName: causaganha-data
```

Apply:
```bash
kubectl apply -f k8s/cronjob-export.yaml
```

## Manual Execution

For testing or one-off exports:

### Export yesterday's data:
```bash
cd /opt/causaganha
source .venv/bin/activate
python scripts/daily_export.py
```

### Export specific date:
```bash
causaganha export-parquet --date 2025-01-15
```

### Export specific tribunal:
```bash
causaganha export-parquet --tribunal TJRO
```

### Backfill historical data:
```bash
causaganha export-parquet --backfill \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

## Monitoring and Alerts

### Exit Codes

The `daily_export.py` script returns:
- **0**: Success (all tribunals exported)
- **1**: Partial failure (some tribunals failed)
- **2**: Complete failure (no tribunals exported)
- **3**: Configuration error

### Alert Integration

**Systemd with email alerts**:

Create `/etc/systemd/system/causaganha-export@.service.d/override.conf`:
```ini
[Service]
OnFailure=failure-email@%n.service
```

**Cron email alerts**:

Cron automatically sends email on failure if `MAILTO` is set.

**Custom alerting**:

Monitor exit codes and send to your alerting system:
```bash
#!/bin/bash
python scripts/daily_export.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  # Send alert to Slack, PagerDuty, etc.
  curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
    -d "{\"text\":\"CausaGanha export failed with code $EXIT_CODE\"}"
fi

exit $EXIT_CODE
```

### Health Checks

**Check recent exports**:
```bash
causaganha export-status --days 7
```

**Check failed exports**:
```bash
causaganha export-status --failed-only
```

**Query database directly**:
```sql
-- Recent export statistics
SELECT * FROM export_statistics
ORDER BY partition_date DESC
LIMIT 7;

-- Problematic tribunals
SELECT * FROM problematic_tribunals
WHERE failure_rate_pct > 10;

-- Storage growth
SELECT * FROM storage_growth
ORDER BY month DESC
LIMIT 12;
```

## Troubleshooting

### Export fails immediately

**Check logs**:
```bash
sudo journalctl -u causaganha-export.service -n 50
```

**Common issues**:
- Missing IA credentials
- Database not accessible
- Network connectivity issues
- Insufficient disk space

**Solution**:
```bash
# Test manually
cd /opt/causaganha
source .venv/bin/activate
python scripts/daily_export.py
```

### Some tribunals consistently fail

**Identify problematic tribunals**:
```bash
causaganha export-status --failed-only
```

**Check tribunal-specific errors**:
```sql
SELECT tribunal, error_message, COUNT(*) as failure_count
FROM parquet_exports
WHERE status = 'failed'
GROUP BY tribunal, error_message
ORDER BY failure_count DESC;
```

**Solutions**:
- Check if data exists for that tribunal
- Verify tribunal code is correct
- Check for data quality issues

### Upload to Internet Archive fails

**Check IA connectivity**:
```bash
ia help
```

**Verify credentials**:
```bash
ia configure
```

**Check IA status**: Visit https://archive.org/services/status

**Retry failed uploads**:
```bash
# Re-export failed date
causaganha export-parquet --date 2025-01-15
```

### Timer doesn't run

**Check timer is enabled**:
```bash
systemctl is-enabled causaganha-export.timer
```

**Check next run time**:
```bash
systemctl list-timers causaganha-export.timer
```

**Check timer logs**:
```bash
sudo journalctl -u causaganha-export.timer
```

## Performance Tuning

### Adjust timing

To change the export time, edit the timer file:
```bash
sudo nano /etc/systemd/system/causaganha-export.timer
```

Change `OnCalendar=*-*-* 02:00:00 UTC` to your desired time.

### Resource limits

Edit service file to adjust CPU/memory limits:
```bash
sudo nano /etc/systemd/system/causaganha-export.service
```

Adjust `MemoryMax` and `CPUQuota` as needed.

### Parallel exports

For faster exports, modify the orchestrator to use asyncio parallelism (currently sequential).

## Security Best Practices

1. **Run as dedicated user** (not root)
2. **Restrict file permissions**:
   ```bash
   chmod 600 /opt/causaganha/.env
   chmod 700 /opt/causaganha/data
   ```
3. **Use systemd sandboxing** (already configured in service file)
4. **Rotate logs regularly**:
   ```bash
   sudo nano /etc/logrotate.d/causaganha
   ```
   ```
   /var/log/causaganha/*.log {
       daily
       missingok
       rotate 30
       compress
       delaycompress
       notifempty
       create 0640 causaganha causaganha
   }
   ```

## Backup and Disaster Recovery

### Database backup

Before major operations, backup the DuckDB database:
```bash
cp data/causaganha.duckdb data/causaganha.duckdb.backup
```

### Recovery from Internet Archive

If local database is lost, data can be reconstructed from IA:
```bash
# List all exports
ia search "collection:causaganha"

# Download specific export
ia download causaganha-2025-01-15-TJRO
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/franklinbaldo/causaganha/issues
- Documentation: `docs/`
- Logs: `sudo journalctl -u causaganha-export.service`
