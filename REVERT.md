# Emergency Revert Instructions

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
