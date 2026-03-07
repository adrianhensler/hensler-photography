# Backup and Restore Guide

## Overview

Backups use a simple shell script with no external dependencies. The script runs twice weekly (Mon/Thu at 2 AM), copies the SQLite database and gallery images, and keeps the 2 most recent backups. No container downtime — SQLite's online backup mode is used.

**Disaster recovery** is provided by Hostinger's weekly VPS snapshots (full server image). Local backups protect against accidental data deletion or database corruption between snapshots.

---

## What Gets Backed Up

| Data | Location | Notes |
|------|----------|-------|
| SQLite database | `/opt/backups/hensler_photography/<timestamp>/gallery.db` | Image metadata, users, analytics |
| Gallery images | `/opt/backups/hensler_photography/<timestamp>/gallery-images/` | Originals + WebP variants |

**Not backed up locally** (covered by GitHub or Hostinger):
- Git repository → GitHub
- Site static files (`sites/`) → GitHub
- Docker/Caddy config → GitHub
- Full server state → Hostinger weekly VPS snapshot

---

## Automated Backups

Scheduled via root crontab (Mon and Thu at 2 AM):

```
0 2 * * 1,4 /opt/prod/hensler_photography/scripts/backup.sh >> /opt/prod/hensler_photography/scripts/backup.log 2>&1
```

Verify the cron is set:
```bash
sudo crontab -l
```

---

## Manual Backup

```bash
sudo /opt/prod/hensler_photography/scripts/backup.sh
```

Output example:
```
[2026-03-07 18:28:16] Backup started -> /opt/backups/hensler_photography/20260307_182816
[2026-03-07 18:28:16] Database backed up (1.5M)
[2026-03-07 18:28:16] Images backed up (181 files, 137M)
[2026-03-07 18:28:16] Backup complete: 20260307_182816
[2026-03-07 18:28:16] Backups retained: 2
```

---

## Viewing Backups

```bash
# List all backups
ls /opt/backups/hensler_photography/

# Check backup logs
tail -50 /opt/prod/hensler_photography/scripts/backup.log

# Check backup sizes
du -sh /opt/backups/hensler_photography/*/
```

---

## Restore Database

**When to use**: Database corrupted, images accidentally deleted, data rolled back.

```bash
# List available backups
ls /opt/backups/hensler_photography/

# Copy backup db over the live db (container keeps running)
BACKUP=/opt/backups/hensler_photography/<timestamp>
DB_VOLUME=/var/lib/docker/volumes/hensler_photography_gallery-db/_data

sudo cp "$DB_VOLUME/gallery.db" "$DB_VOLUME/gallery.db.pre-restore"
sudo cp "$BACKUP/gallery.db" "$DB_VOLUME/gallery.db"

# Restart API to pick up restored database
cd /opt/prod/hensler_photography
docker compose restart api

# Verify
docker compose exec api python3 -c "
import sqlite3
conn = sqlite3.connect('/data/gallery.db')
count = conn.execute('SELECT COUNT(*) FROM images').fetchone()[0]
print(f'Database OK: {count} images')
"
```

---

## Restore Gallery Images

```bash
BACKUP=/opt/backups/hensler_photography/<timestamp>
IMAGES_VOLUME=/var/lib/docker/volumes/hensler_photography_gallery-images/_data

# Copy restored images into the volume
sudo cp -a "$BACKUP/gallery-images/." "$IMAGES_VOLUME/"
```

---

## Complete Server Rebuild

If the VPS is lost entirely, restore from the Hostinger weekly snapshot (preferred), or rebuild manually:

```bash
# 1. Provision new VPS, install Docker
curl -fsSL https://get.docker.com | sh

# 2. Clone repository
git clone https://github.com/adrianhensler/hensler-photography.git /opt/prod/hensler_photography

# 3. Transfer backup files from old server (or Hostinger snapshot)
rsync -avz old-server:/opt/backups/hensler_photography/ /opt/backups/hensler_photography/

# 4. Start production stack
cd /opt/prod/hensler_photography
docker compose up -d

# 5. Restore database and images (see sections above)

# 6. Verify health
curl -I https://hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

---

## Retention

The script keeps the **2 most recent backups** and deletes older ones automatically. Each backup is approximately 140MB based on current data (1.5MB database + ~137MB images).

To change retention, edit `KEEP=2` in `scripts/backup.sh`.

---

## Troubleshooting

**Script fails: "sqlite3 not installed"**
```bash
sudo apt install sqlite3
```

**Script fails: "Database not found"**
```bash
# Check the volume exists and has data
ls /var/lib/docker/volumes/hensler_photography_gallery-db/_data/
```

**Check disk space before backup**
```bash
df -h /opt/backups
```

**Out of disk space — emergency prune**
```bash
# Remove oldest backup manually
ls /opt/backups/hensler_photography/
sudo rm -rf /opt/backups/hensler_photography/<oldest-timestamp>
```

---

## Recovery Time Objectives

| Scenario | Method | Est. Time |
|----------|--------|-----------|
| Accidental image/data deletion | Local backup restore | 5 minutes |
| Database corruption | Local backup restore | 5 minutes |
| Full server loss | Hostinger VPS snapshot | 30–60 minutes |

**Maximum data loss**: 3–4 days (worst case between local backups, covered by Hostinger weekly snapshot).
