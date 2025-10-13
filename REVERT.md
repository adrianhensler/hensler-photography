# Rollback and Revert Instructions

This document covers multiple rollback strategies depending on the situation.

---

## Option 1: Git-Based Rollback (Recommended)

Use this when the current code version has issues and you want to rollback to a previous tagged version.

### Quick Rollback

```bash
# List available versions
git tag -l

# Example output:
# v1.0.0
# v1.1.0
# v1.2.0

# Checkout previous working version
git checkout v1.1.0

# Restart production with old version
cd /opt/testing/hensler_photography
docker compose restart

# Verify rollback worked
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

### After Rollback

```bash
# Document the issue
# Fix the problem in a new branch or locally

# When ready to return to latest code
git checkout main

# Or create a fix
git checkout -b fix-issue
# ... make fixes ...
git add .
git commit -m "Fix issue that required rollback"
git push origin fix-issue
```

### Rollback with Git Reset (Use Carefully)

If you've committed bad code to main and want to undo it:

```bash
# See recent commits
git log --oneline -5

# Reset to previous commit (does not push)
git reset --hard <commit-hash>

# Force push to GitHub (DANGEROUS - only if necessary)
git push --force origin main

# Restart production
docker compose restart
```

**Warning**: Force pushing rewrites history. Only do this if:
- No one else has pulled the bad commits
- You understand the implications
- You have backups

---

## Option 2: Restore from Backup

Use this when files are corrupted or accidentally deleted.

See **BACKUP.md** for complete restore procedures.

### Quick Restore

```bash
# List available backups
restic -r /opt/backups/hensler_photography snapshots

# Restore specific files from backup
restic -r /opt/backups/hensler_photography restore <snapshot-id> \
  --target /tmp/restore \
  --path /opt/testing/hensler_photography/sites

# Copy restored files back
cp -r /tmp/restore/opt/testing/hensler_photography/sites/* \
  /opt/testing/hensler_photography/sites/

# Restart production
docker compose restart
```

---

## Option 3: Emergency Revert to Old Single-Site Production

If you need to rollback to the old single-site production:

## Quick Revert
```bash
# Stop new production
cd /opt/testing/hensler_photography
docker compose down

# Start old production
cd /opt/liam_site_project
docker compose up -d
```

## What This Does
- Stops the new three-site setup
- Restarts the old liam_site_project (which still has all its TLS certificates)
- Reverts to only serving liam.hensler.photography

## After Revert
- liam.hensler.photography will work immediately (has existing certs)
- adrian.hensler.photography and hensler.photography will not work (not in old config)
- Old production container name: liam_site_project-web-1

## Full Rollback Path
The old production setup is preserved at:
- `/opt/liam_site_project/` (unchanged)
- Docker volumes with TLS certs still exist
