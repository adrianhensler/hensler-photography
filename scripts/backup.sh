#!/bin/bash
set -euo pipefail

################################################################################
# Hensler Photography - Backup Script
#
# This script backs up Docker volumes containing TLS certificates and Caddy
# configuration using restic. It stops the production container during backup
# to ensure data consistency, then restarts it.
#
# Usage:
#   sudo ./scripts/backup.sh
#
# Requirements:
#   - restic installed (https://restic.net)
#   - Restic repository initialized at /opt/backups/hensler_photography
#   - RESTIC_PASSWORD environment variable set
#
# Cron example (daily at 2 AM):
#   0 2 * * * cd /opt/testing/hensler_photography && sudo -E ./scripts/backup.sh >> /opt/testing/hensler_photography/scripts/backup.log 2>&1
################################################################################

# Configuration
BACKUP_REPO="/opt/backups/hensler_photography"
PROJECT_DIR="/opt/testing/hensler_photography"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.yml"
LOG_FILE="${PROJECT_DIR}/scripts/backup.log"
RETENTION_DAYS=7
RETENTION_WEEKS=4
RETENTION_MONTHS=6

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
    log "Restic repository not found. Initializing at $BACKUP_REPO"
    mkdir -p "$BACKUP_REPO"
    restic -r "$BACKUP_REPO" init
    log "Restic repository initialized"
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    log_error "Docker is not running"
    exit 1
fi

# Start backup process
log "========================================="
log "Starting backup process"
log "========================================="

# Check if production container is running
cd "$PROJECT_DIR"
CONTAINER_RUNNING=false
if docker compose ps | grep -q "Up"; then
    CONTAINER_RUNNING=true
    log "Production container is running - will stop for backup"
else
    log "Production container is not running"
fi

# Stop production container for consistent backup
if [ "$CONTAINER_RUNNING" = true ]; then
    log "Stopping production container..."
    docker compose down
    sleep 3
    log "Production container stopped"
fi

# Get volume mount points
CADDY_DATA_VOLUME=$(docker volume inspect hensler_photography_caddy-data --format '{{ .Mountpoint }}' 2>/dev/null || echo "")
CADDY_CONFIG_VOLUME=$(docker volume inspect hensler_photography_caddy-config --format '{{ .Mountpoint }}' 2>/dev/null || echo "")

if [ -z "$CADDY_DATA_VOLUME" ] || [ -z "$CADDY_CONFIG_VOLUME" ]; then
    log_error "Could not find Docker volumes. They may not exist yet."
    log_error "Run 'docker compose up -d' first to create volumes."
    exit 1
fi

# Backup Docker volumes
log "Backing up Docker volumes..."
log "  - caddy-data: $CADDY_DATA_VOLUME"
log "  - caddy-config: $CADDY_CONFIG_VOLUME"

restic -r "$BACKUP_REPO" backup \
    "$CADDY_DATA_VOLUME" \
    "$CADDY_CONFIG_VOLUME" \
    --tag docker-volumes \
    --tag production \
    --host hensler-photography

BACKUP_EXIT_CODE=$?

if [ $BACKUP_EXIT_CODE -eq 0 ]; then
    log "Docker volumes backed up successfully"
else
    log_error "Backup failed with exit code $BACKUP_EXIT_CODE"
fi

# Backup site content (files)
log "Backing up site content..."
restic -r "$BACKUP_REPO" backup \
    "${PROJECT_DIR}/sites" \
    "${PROJECT_DIR}/Caddyfile" \
    "${PROJECT_DIR}/docker-compose.yml" \
    --tag site-content \
    --tag production \
    --host hensler-photography

CONTENT_BACKUP_EXIT_CODE=$?

if [ $CONTENT_BACKUP_EXIT_CODE -eq 0 ]; then
    log "Site content backed up successfully"
else
    log_error "Site content backup failed with exit code $CONTENT_BACKUP_EXIT_CODE"
fi

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

# Apply retention policy
log "Applying retention policy..."
restic -r "$BACKUP_REPO" forget \
    --keep-daily "$RETENTION_DAYS" \
    --keep-weekly "$RETENTION_WEEKS" \
    --keep-monthly "$RETENTION_MONTHS" \
    --prune

FORGET_EXIT_CODE=$?

if [ $FORGET_EXIT_CODE -eq 0 ]; then
    log "Retention policy applied successfully"
else
    log_error "Failed to apply retention policy (exit code $FORGET_EXIT_CODE)"
fi

# Show backup statistics
log "Backup statistics:"
restic -r "$BACKUP_REPO" snapshots --compact | tail -n 10 | tee -a "$LOG_FILE"

# Check repository health
log "Checking repository health..."
restic -r "$BACKUP_REPO" check --read-data-subset=5%

CHECK_EXIT_CODE=$?

if [ $CHECK_EXIT_CODE -eq 0 ]; then
    log "Repository health check passed"
else
    log_error "Repository health check failed (exit code $CHECK_EXIT_CODE)"
fi

# Final status
log "========================================="
if [ $BACKUP_EXIT_CODE -eq 0 ] && [ $CONTENT_BACKUP_EXIT_CODE -eq 0 ]; then
    log "✓ Backup completed successfully"
    log "========================================="
    exit 0
else
    log_error "✗ Backup completed with errors"
    log "========================================="
    exit 1
fi
