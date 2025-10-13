# Backup and Restore Guide

## Overview

This project uses [restic](https://restic.net/) for automated backups of critical data including Docker volumes (TLS certificates) and site content. Automated daily backups run at 2 AM with a retention policy of 7 daily, 4 weekly, and 6 monthly snapshots.

---

## What Gets Backed Up

### Docker Volumes
- **caddy-data**: TLS certificates from Let's Encrypt
- **caddy-config**: Caddy server configuration cache

### Site Content
- `sites/` directory (all three sites)
- `Caddyfile` (production configuration)
- `docker-compose.yml` (production orchestration)

### What's NOT Backed Up
- Git repository (backed up to GitHub)
- Node modules (reinstall with `npm install`)
- Test environment (docker-compose.local.yml)
- Logs and temporary files

---

## Initial Setup

### 1. Install Restic

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install restic

# Verify installation
restic version
```

### 2. Set Backup Password

Choose a strong password for encrypting backups:

```bash
# Create password file (secure location)
echo "YOUR-STRONG-PASSWORD" | sudo tee /root/.restic-password > /dev/null
sudo chmod 600 /root/.restic-password

# Or export for current session
export RESTIC_PASSWORD="YOUR-STRONG-PASSWORD"
```

**Important**: Store this password securely. Without it, backups cannot be restored.

### 3. Initialize Backup Repository

```bash
# Create backup directory
sudo mkdir -p /opt/backups/hensler_photography

# Initialize restic repository
sudo RESTIC_PASSWORD=$(cat /root/.restic-password) \
  restic -r /opt/backups/hensler_photography init
```

### 4. Setup Automated Backups

Add cron job for daily backups:

```bash
# Edit root's crontab
sudo crontab -e

# Add this line (runs daily at 2 AM):
0 2 * * * export RESTIC_PASSWORD=$(cat /root/.restic-password) && cd /opt/testing/hensler_photography && /opt/testing/hensler_photography/scripts/backup.sh >> /opt/testing/hensler_photography/scripts/backup.log 2>&1
```

---

## Manual Backup

To create a backup immediately:

```bash
# Export password
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

# Run backup script
cd /opt/testing/hensler_photography
sudo -E ./scripts/backup.sh
```

**What happens:**
1. Production container stops (prevents data corruption)
2. Docker volumes backed up
3. Site content backed up
4. Production container restarts
5. Retention policy applied
6. Repository health check performed

**Downtime**: ~30 seconds while container is stopped.

---

## Viewing Backups

### List All Snapshots

```bash
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)
restic -r /opt/backups/hensler_photography snapshots
```

Example output:
```
ID        Time                 Host                  Tags             Paths
----------------------------------------------------------------------------------
a1b2c3d4  2025-10-13 02:00:15  hensler-photography  docker-volumes   /var/lib/docker/volumes/...
e5f6g7h8  2025-10-13 02:00:30  hensler-photography  site-content     /opt/testing/hensler_photography/sites
```

### Show Snapshot Details

```bash
restic -r /opt/backups/hensler_photography snapshots <snapshot-id>
```

### List Files in Snapshot

```bash
restic -r /opt/backups/hensler_photography ls <snapshot-id>
```

### Check Repository Stats

```bash
restic -r /opt/backups/hensler_photography stats
```

---

## Restoring from Backup

### Full Restore

Use the restore script to restore everything:

```bash
# Export password
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

# List available backups
sudo -E ./scripts/restore.sh

# Restore from specific snapshot
sudo -E ./scripts/restore.sh <snapshot-id>
```

**What happens:**
1. Shows snapshot details and asks for confirmation
2. Production container stops
3. Data restored to temporary location
4. Docker volumes overwritten
5. Site content optionally overwritten
6. Production container restarts

### Selective Restore

To restore only specific files:

```bash
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

# Restore to temporary location
restic -r /opt/backups/hensler_photography restore <snapshot-id> \
  --target /tmp/restore

# Copy specific files you need
sudo cp -a /tmp/restore/path/to/file /destination/

# Clean up
rm -rf /tmp/restore
```

### Restore Only TLS Certificates

```bash
# Find volume mount point
VOLUME_PATH=$(docker volume inspect hensler_photography_caddy-data --format '{{ .Mountpoint }}')

# Stop container
docker compose down

# Restore volume
restic -r /opt/backups/hensler_photography restore <snapshot-id> \
  --target /tmp/restore \
  --path "$VOLUME_PATH"

# Copy data
sudo cp -a /tmp/restore"$VOLUME_PATH"/* "$VOLUME_PATH"/

# Restart container
docker compose up -d

# Clean up
rm -rf /tmp/restore
```

---

## Retention Policy

Automated backups follow this retention schedule:

- **Daily**: Keep last 7 days
- **Weekly**: Keep last 4 weeks
- **Monthly**: Keep last 6 months

Older snapshots are automatically pruned.

### Modifying Retention

Edit `scripts/backup.sh` and change these variables:

```bash
RETENTION_DAYS=7    # Daily snapshots to keep
RETENTION_WEEKS=4   # Weekly snapshots to keep
RETENTION_MONTHS=6  # Monthly snapshots to keep
```

### Manual Cleanup

To manually apply retention policy:

```bash
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

restic -r /opt/backups/hensler_photography forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 6 \
  --prune
```

---

## Backup Storage

### Current Setup

Backups stored locally at `/opt/backups/hensler_photography/`

### Recommended: Add Remote Backup

For additional safety, sync backups to remote storage:

**Option 1: rsync to another server**
```bash
# After backup runs, sync to remote server
rsync -avz --delete /opt/backups/hensler_photography/ \
  user@backup-server:/backups/hensler_photography/
```

**Option 2: Restic to S3/B2/other cloud**
```bash
# Initialize remote repository
restic -r s3:s3.amazonaws.com/bucket-name init

# Copy snapshots to remote
restic -r /opt/backups/hensler_photography copy \
  --repo2 s3:s3.amazonaws.com/bucket-name
```

**Option 3: Automated cloud sync via cron**
```bash
# Add to crontab after backup job
30 2 * * * rsync -avz /opt/backups/hensler_photography/ user@remote:/backups/
```

---

## Monitoring Backups

### Check Last Backup

```bash
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)
restic -r /opt/backups/hensler_photography snapshots --last 1
```

### View Backup Logs

```bash
tail -n 50 /opt/testing/hensler_photography/scripts/backup.log
```

### Email Notifications

To get notified of backup failures, modify the cron job:

```bash
# Install mailutils
sudo apt install mailutils

# Update crontab to send email on failure:
0 2 * * * cd /opt/testing/hensler_photography && export RESTIC_PASSWORD=$(sudo cat /root/.restic-password) && /opt/testing/hensler_photography/scripts/backup.sh || echo "Backup failed!" | mail -s "Hensler Photography Backup Failed" your@email.com
```

### External Monitoring

Consider using [Healthchecks.io](https://healthchecks.io) for backup monitoring:

```bash
# Add to backup.sh at the end
curl -fsS -m 10 --retry 5 https://hc-ping.com/YOUR-UUID
```

---

## Disaster Recovery Scenarios

### Scenario 1: Accidental File Deletion

```bash
# List recent backups
sudo -E ./scripts/restore.sh

# Restore from yesterday's backup
sudo -E ./scripts/restore.sh <snapshot-id>

# Selectively copy back deleted files
```

### Scenario 2: Corrupted TLS Certificates

```bash
# Stop container
docker compose down

# Restore caddy-data volume from backup
# (see "Restore Only TLS Certificates" above)

# Restart
docker compose up -d
```

### Scenario 3: Complete Server Failure

On new server:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Install restic
sudo apt install restic

# Clone repository
git clone https://github.com/adrianhensler/hensler-photography.git
cd hensler-photography

# Copy backup repository from old server (or restore from remote)
rsync -avz old-server:/opt/backups/hensler_photography/ /opt/backups/hensler_photography/

# Restore using script
export RESTIC_PASSWORD="your-password"
sudo -E ./scripts/restore.sh <snapshot-id>

# Start production
docker compose up -d
```

---

## Backup Best Practices

### Do's
- ✅ Test restore procedures regularly (quarterly)
- ✅ Monitor backup success (check logs weekly)
- ✅ Keep backups in multiple locations (local + remote)
- ✅ Secure backup password (password manager, encrypted file)
- ✅ Verify backup integrity with `restic check`
- ✅ Document restore procedures (this file!)

### Don'ts
- ❌ Don't rely only on local backups (disk failure risk)
- ❌ Don't forget backup password (unrecoverable without it)
- ❌ Don't skip testing restores (backup untested = backup broken)
- ❌ Don't store backup password in plaintext in git
- ❌ Don't ignore backup failure notifications
- ❌ Don't delete old snapshots manually (use retention policy)

---

## Troubleshooting

### Backup Script Fails

```bash
# Check logs
tail -n 100 /opt/testing/hensler_photography/scripts/backup.log

# Common issues:
# 1. RESTIC_PASSWORD not set
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

# 2. Repository locked (previous backup interrupted)
restic -r /opt/backups/hensler_photography unlock

# 3. Insufficient disk space
df -h /opt/backups

# 4. Docker not running
docker info
```

### Restore Fails

```bash
# Check repository integrity
restic -r /opt/backups/hensler_photography check

# Repair repository if needed
restic -r /opt/backups/hensler_photography rebuild-index
```

### Repository Locked

```bash
# If backup was interrupted, repository may be locked
restic -r /opt/backups/hensler_photography unlock
```

### Out of Disk Space

```bash
# Check usage
df -h /opt/backups

# Remove old snapshots manually
restic -r /opt/backups/hensler_photography forget <snapshot-id>
restic -r /opt/backups/hensler_photography prune
```

---

## Recovery Time Objectives (RTO)

Expected recovery times:

| Scenario | Recovery Time | Data Loss |
|----------|---------------|-----------|
| Single file restore | 5 minutes | None (from last backup) |
| Full site restore | 15 minutes | None (from last backup) |
| TLS certificate restore | 10 minutes | None (from last backup) |
| Complete server rebuild | 1-2 hours | None (from last backup) |

**Maximum data loss**: 24 hours (time since last backup)

To reduce data loss window, increase backup frequency:
```bash
# Backup every 6 hours instead of daily
0 */6 * * * ...backup command...
```

---

## Security Considerations

### Backup Encryption

Restic encrypts all backups with AES-256. Your `RESTIC_PASSWORD` is the encryption key.

**Important**: Anyone with access to the backup files AND the password can read your backups.

### Password Security

```bash
# Secure the password file
sudo chmod 600 /root/.restic-password
sudo chown root:root /root/.restic-password

# Verify permissions
ls -l /root/.restic-password
# Should show: -rw------- 1 root root
```

### Backup Location Security

```bash
# Secure backup directory
sudo chmod 700 /opt/backups
sudo chown root:root /opt/backups
```

---

## Additional Resources

- **Restic Documentation**: https://restic.readthedocs.io/
- **Restic Forum**: https://forum.restic.net/
- **GitHub Issues**: https://github.com/restic/restic/issues

---

## Quick Reference

```bash
# Export password (required for all commands)
export RESTIC_PASSWORD=$(sudo cat /root/.restic-password)

# Manual backup
sudo -E ./scripts/backup.sh

# List backups
restic -r /opt/backups/hensler_photography snapshots

# Restore
sudo -E ./scripts/restore.sh <snapshot-id>

# Check repository health
restic -r /opt/backups/hensler_photography check

# View backup size
restic -r /opt/backups/hensler_photography stats

# Unlock locked repository
restic -r /opt/backups/hensler_photography unlock
```
