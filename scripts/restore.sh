#!/bin/bash
set -euo pipefail

################################################################################
# Hensler Photography - Restore Script
#
# This script restores Docker volumes and site content from restic backups.
# Use this to recover from data loss, corruption, or to rollback to a previous
# state.
#
# Usage:
#   sudo ./scripts/restore.sh [snapshot-id]
#
#   If snapshot-id is not provided, will show available snapshots and prompt.
#
# Requirements:
#   - restic installed (https://restic.net)
#   - Restic repository exists at /opt/backups/hensler_photography
#   - RESTIC_PASSWORD environment variable set
################################################################################

# Configuration
BACKUP_REPO="/opt/backups/hensler_photography"
PROJECT_DIR="/opt/testing/hensler_photography"
RESTORE_TEMP="/tmp/hensler_restore_$(date +%s)"
LOG_FILE="${PROJECT_DIR}/scripts/restore.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$LOG_FILE" >&2
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

# Check if restic is installed
if ! command -v restic &> /dev/null; then
    log_error "restic is not installed. Install with: apt install restic"
    exit 1
fi

# Check if RESTIC_PASSWORD is set
if [ -z "${RESTIC_PASSWORD:-}" ]; then
    log_error "RESTIC_PASSWORD environment variable is not set"
    log_error "Set it with: export RESTIC_PASSWORD='your-secure-password'"
    exit 1
fi

# Check if repository exists
if [ ! -d "$BACKUP_REPO" ]; then
    log_error "Restic repository not found at $BACKUP_REPO"
    exit 1
fi

# Start restore process
log "========================================="
log "Starting restore process"
log "========================================="

# If snapshot ID not provided, show available snapshots
SNAPSHOT_ID="${1:-}"

if [ -z "$SNAPSHOT_ID" ]; then
    log "Available backups:"
    echo ""
    restic -r "$BACKUP_REPO" snapshots
    echo ""
    echo "Usage: sudo ./scripts/restore.sh <snapshot-id>"
    echo "Example: sudo ./scripts/restore.sh a1b2c3d4"
    exit 0
fi

# Verify snapshot exists
log "Verifying snapshot $SNAPSHOT_ID exists..."
if ! restic -r "$BACKUP_REPO" snapshots "$SNAPSHOT_ID" &>/dev/null; then
    log_error "Snapshot $SNAPSHOT_ID not found"
    log "Run without arguments to see available snapshots"
    exit 1
fi

# Show snapshot details
log "Snapshot details:"
restic -r "$BACKUP_REPO" snapshots "$SNAPSHOT_ID" | tee -a "$LOG_FILE"
echo ""

# Confirm restore
read -p "Restore from this snapshot? This will OVERWRITE current data. (yes/no): " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    log "Restore cancelled by user"
    exit 0
fi

# Create temporary restore directory
mkdir -p "$RESTORE_TEMP"
log "Temporary restore directory: $RESTORE_TEMP"

# Stop production container
log "Stopping production container..."
cd "$PROJECT_DIR"
CONTAINER_RUNNING=false
if docker compose ps | grep -q "Up"; then
    CONTAINER_RUNNING=true
    docker compose down
    sleep 3
    log "Production container stopped"
fi

# Restore from snapshot
log "Restoring data from snapshot $SNAPSHOT_ID..."
restic -r "$BACKUP_REPO" restore "$SNAPSHOT_ID" --target "$RESTORE_TEMP"

RESTORE_EXIT_CODE=$?

if [ $RESTORE_EXIT_CODE -ne 0 ]; then
    log_error "Restore failed with exit code $RESTORE_EXIT_CODE"
    exit 1
fi

log "Data restored to temporary location"

# Get volume mount points
CADDY_DATA_VOLUME=$(docker volume inspect hensler_photography_caddy-data --format '{{ .Mountpoint }}' 2>/dev/null || echo "")
CADDY_CONFIG_VOLUME=$(docker volume inspect hensler_photography_caddy-config --format '{{ .Mountpoint }}' 2>/dev/null || echo "")

# Find restored volume data in temp directory
RESTORED_DATA=$(find "$RESTORE_TEMP" -type d -name "caddy-data" | head -n1)
RESTORED_CONFIG=$(find "$RESTORE_TEMP" -type d -name "caddy-config" | head -n1)

# Restore Docker volumes if found
if [ -n "$RESTORED_DATA" ] && [ -n "$CADDY_DATA_VOLUME" ]; then
    log "Restoring caddy-data volume..."
    rm -rf "${CADDY_DATA_VOLUME:?}"/*
    cp -a "$RESTORED_DATA"/* "$CADDY_DATA_VOLUME"/
    log "caddy-data volume restored"
fi

if [ -n "$RESTORED_CONFIG" ] && [ -n "$CADDY_CONFIG_VOLUME" ]; then
    log "Restoring caddy-config volume..."
    rm -rf "${CADDY_CONFIG_VOLUME:?}"/*
    cp -a "$RESTORED_CONFIG"/* "$CADDY_CONFIG_VOLUME"/
    log "caddy-config volume restored"
fi

# Restore site content if found
RESTORED_SITES=$(find "$RESTORE_TEMP" -type d -path "*/hensler_photography/sites" | head -n1)
if [ -n "$RESTORED_SITES" ]; then
    log "Restoring site content..."
    read -p "Overwrite sites/ directory? (yes/no): " -r
    echo
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        rm -rf "${PROJECT_DIR}/sites"
        cp -a "$RESTORED_SITES" "${PROJECT_DIR}/sites"
        log "Site content restored"
    else
        log "Skipped site content restore"
    fi
fi

# Restore Caddyfile if found
RESTORED_CADDYFILE=$(find "$RESTORE_TEMP" -type f -path "*/hensler_photography/Caddyfile" | head -n1)
if [ -n "$RESTORED_CADDYFILE" ]; then
    log "Restoring Caddyfile..."
    cp "$RESTORED_CADDYFILE" "${PROJECT_DIR}/Caddyfile"
    log "Caddyfile restored"
fi

# Restore docker-compose.yml if found
RESTORED_COMPOSE=$(find "$RESTORE_TEMP" -type f -path "*/hensler_photography/docker-compose.yml" | head -n1)
if [ -n "$RESTORED_COMPOSE" ]; then
    log "Restoring docker-compose.yml..."
    cp "$RESTORED_COMPOSE" "${PROJECT_DIR}/docker-compose.yml"
    log "docker-compose.yml restored"
fi

# Clean up temporary directory
log "Cleaning up temporary files..."
rm -rf "$RESTORE_TEMP"
log "Temporary files removed"

# Restart production container
if [ "$CONTAINER_RUNNING" = true ]; then
    log "Restarting production container..."
    docker compose up -d
    sleep 5

    # Verify container started
    if docker compose ps | grep -q "Up"; then
        log "Production container restarted successfully"
    else
        log_error "Failed to restart production container!"
        docker compose logs --tail=20 web
        exit 1
    fi
fi

# Final status
log "========================================="
log "✓ Restore completed successfully"
log "========================================="
log ""
log "Next steps:"
log "1. Verify sites are working:"
log "   curl -I https://hensler.photography/healthz"
log "   curl -I https://liam.hensler.photography/healthz"
log "   curl -I https://adrian.hensler.photography/healthz"
log ""
log "2. Check git status:"
log "   cd $PROJECT_DIR && git status"
log ""
log "3. If files changed, commit or reset as needed"

exit 0
