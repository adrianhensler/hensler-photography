#!/bin/bash
set -euo pipefail

################################################################################
# Hensler Photography - Backup Script
#
# Backs up the SQLite database and gallery images to /opt/backups/hensler_photography.
# Keeps the 2 most recent backups. No container downtime (SQLite online backup).
#
# Usage:
#   sudo ./scripts/backup.sh
#
# Cron (twice weekly, Mon and Thu at 2 AM):
#   0 2 * * 1,4 cd /opt/prod/hensler_photography && sudo ./scripts/backup.sh >> /opt/prod/hensler_photography/scripts/backup.log 2>&1
################################################################################

BACKUP_ROOT="/opt/backups/hensler_photography"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
DEST="${BACKUP_ROOT}/${TIMESTAMP}"
LOG_FILE="/opt/prod/hensler_photography/scripts/backup.log"
KEEP=2

DB_VOLUME="/var/lib/docker/volumes/hensler_photography_gallery-db/_data"
IMAGES_VOLUME="/var/lib/docker/volumes/hensler_photography_gallery-images/_data"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2; }

if [ "$EUID" -ne 0 ]; then
    log_error "Must be run as root (use sudo)"
    exit 1
fi

if ! command -v sqlite3 &>/dev/null; then
    log_error "sqlite3 not installed: apt install sqlite3"
    exit 1
fi

log "============================="
log "Backup started -> ${DEST}"
log "============================="

mkdir -p "$DEST"

# SQLite online backup (no container stop needed)
DB_SRC="${DB_VOLUME}/gallery.db"
if [ -f "$DB_SRC" ]; then
    log "Backing up database..."
    sqlite3 "$DB_SRC" ".backup '${DEST}/gallery.db'"
    log "Database backed up ($(du -sh "${DEST}/gallery.db" | cut -f1))"
else
    log_error "Database not found at $DB_SRC"
    exit 1
fi

# Copy gallery images
if [ -d "$IMAGES_VOLUME" ]; then
    log "Backing up gallery images..."
    cp -a "$IMAGES_VOLUME" "${DEST}/gallery-images"
    IMAGE_COUNT=$(find "${DEST}/gallery-images" -type f | wc -l)
    log "Images backed up ($IMAGE_COUNT files, $(du -sh "${DEST}/gallery-images" | cut -f1))"
else
    log "Images volume not found, skipping"
fi

# Prune old backups, keep $KEEP most recent
BACKUP_COUNT=$(ls -1d "${BACKUP_ROOT}"/[0-9]* 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt "$KEEP" ]; then
    TO_DELETE=$(ls -1d "${BACKUP_ROOT}"/[0-9]* | head -n $(( BACKUP_COUNT - KEEP )))
    for OLD in $TO_DELETE; do
        log "Removing old backup: $(basename "$OLD")"
        rm -rf "$OLD"
    done
fi

log "============================="
log "Backup complete: ${TIMESTAMP}"
log "Backups retained: $(ls -1d "${BACKUP_ROOT}"/[0-9]* 2>/dev/null | wc -l)"
log "============================="
