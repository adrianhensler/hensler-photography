# CI/CD Automation & Workflow Improvements

## Goal: Catch Mistakes Before Production

**Current Problem:**
- CI tests don't run (broken setup)
- No automated checks
- Manual deployment prone to human error
- Can't catch issues until production

---

## Priority 1: Fix CI Tests (Immediate)

### Current Issue:

GitHub Actions can't find `package-lock.json` during checkout. Tests never run.

### Fix:

**.github/workflows/test.yml** needs updating:

```yaml
name: Automated Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'  # ← This line causes issues if package-lock.json location is unexpected

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Start test server
        run: |
          docker compose -f docker-compose.local.yml up -d
          sleep 10  # Wait for server to be ready

      - name: Run Playwright tests
        run: npm test

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/

      - name: Cleanup
        if: always()
        run: docker compose -f docker-compose.local.yml down
```

**Key fix:** Ensure `package-lock.json` is in root directory and checked into git.

---

## Priority 2: Automated Checks on Every PR

### What Should Run Automatically:

**1. Python Syntax Check:**
```yaml
- name: Check Python syntax
  run: |
    pip install flake8
    flake8 api/ --count --select=E9,F63,F7,F82 --show-source --statistics
```

**2. Python Tests:**
```yaml
- name: Run Python tests
  run: |
    pip install -r api/requirements.txt
    pytest api/tests/
```

**3. Frontend Tests:**
```yaml
- name: Run Playwright tests
  run: npm test
```

**4. Docker Build Check:**
```yaml
- name: Verify Docker builds
  run: docker compose build
```

**5. Security Scan:**
```yaml
- name: Security audit
  run: |
    npm audit --audit-level=high
    pip install safety
    safety check
```

---

## Priority 3: Automated Deployment

### GitHub Actions Workflow:

**.github/workflows/deploy.yml:**

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]
    # Only deploy when tests pass

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      # ... same as test.yml ...

  deploy:
    needs: test  # Only deploy if tests pass
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/prod/hensler_photography
            git pull origin main

            # Check if API changes require restart
            if git diff HEAD@{1} --name-only | grep -q "^api/"; then
              echo "API changes detected, restarting..."
              docker compose restart api
            else
              echo "No API changes, skip restart"
            fi

            # Verify deployment
            curl -f https://adrian.hensler.photography/healthz || exit 1
            echo "✅ Deployment successful"
```

**Benefits:**
- ✅ Tests must pass before deploy
- ✅ Automatic deployment on merge to main
- ✅ Smart restart (only API if needed)
- ✅ Health check verification

---

## Priority 4: Pre-Commit Hooks (Catch Issues Locally)

Install pre-commit hooks to catch issues before committing.

### Setup:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=5000']

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100']

  - repo: local
    hooks:
      - id: python-compile-check
        name: Python syntax check
        entry: python -m compileall
        language: system
        types: [python]
EOF

# Install hooks
pre-commit install
```

**Now:** Every `git commit` runs these checks automatically. Bad code can't be committed!

---

## Priority 5: Protected Main Branch

### GitHub Branch Protection Rules:

Go to: Settings → Branches → Add rule for `main`

Enable:
- ✅ Require pull request before merging
- ✅ Require status checks to pass (tests must pass)
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

**Result:** Can't push broken code to main. Ever.

---

## Priority 6: Automatic Rollback on Failure

### Enhanced Deployment Script:

```bash
#!/bin/bash
# deploy-with-rollback.sh

set -e

CURRENT_COMMIT=$(git rev-parse HEAD)

echo "🚀 Deploying commit: $CURRENT_COMMIT"

# Pull latest
git pull origin main
NEW_COMMIT=$(git rev-parse HEAD)

# Restart (if needed)
if git diff $CURRENT_COMMIT $NEW_COMMIT --name-only | grep -q "^api/"; then
    docker compose restart api
fi

# Wait for health check
echo "Waiting for services to be healthy..."
sleep 5

# Verify deployment
if ! curl -sf https://adrian.hensler.photography/healthz > /dev/null; then
    echo "❌ Health check failed! Rolling back..."
    git reset --hard $CURRENT_COMMIT
    docker compose restart

    # Verify rollback
    if curl -sf https://adrian.hensler.photography/healthz > /dev/null; then
        echo "✅ Rollback successful, site restored"
        exit 1
    else
        echo "🚨 CRITICAL: Rollback failed! Manual intervention needed!"
        exit 2
    fi
fi

echo "✅ Deployment successful"
```

**Safety:** If deployment fails, automatically reverts to previous working state.

---

## Priority 7: Monitoring & Alerts

### Simple Uptime Monitor:

```bash
#!/bin/bash
# monitor.sh

SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

while true; do
    if ! curl -sf https://adrian.hensler.photography/healthz > /dev/null; then
        # Site is down!
        curl -X POST $SLACK_WEBHOOK -H 'Content-Type: application/json' \
            -d '{"text":"🚨 adrian.hensler.photography is DOWN!"}'

        # Try to auto-recover
        cd /opt/prod/hensler_photography
        docker compose restart

        sleep 60
    fi

    sleep 30  # Check every 30 seconds
done
```

**Run as systemd service:** Monitor runs 24/7, alerts + auto-recovers on failure.

---

## Recommended Implementation Order

### Week 1 (This Week):
1. ✅ Fix CI test workflow
2. ✅ Add pre-commit hooks
3. ✅ Enable branch protection rules

### Week 2:
4. ✅ Add automated deployment workflow
5. ✅ Create deploy-with-rollback.sh script
6. ✅ Set up basic monitoring

### Week 3:
7. ✅ Add comprehensive test coverage
8. ✅ Set up staging environment automation
9. ✅ Configure alerts (Slack/email)

---

## Success Metrics

**Before (Current State):**
- ❌ CI doesn't run
- ❌ Manual deployments prone to error
- ❌ No automatic rollback
- ❌ No monitoring

**After (Target State):**
- ✅ Every PR tested automatically
- ✅ Can't merge broken code
- ✅ Automatic deployment on merge
- ✅ Auto-rollback on failure
- ✅ 24/7 monitoring with alerts
- ✅ Deployment takes 30 seconds (vs. 5 minutes manual)

---

## Quick Wins (Start Today)

```bash
# 1. Fix package-lock.json location
cd /opt/prod/hensler_photography
ls -la package-lock.json  # Verify it exists in root
git add package-lock.json
git commit -m "Ensure package-lock.json is tracked"
git push

# 2. Install pre-commit hooks
pip install pre-commit
# Create .pre-commit-config.yaml (see above)
pre-commit install

# 3. Enable GitHub branch protection
# Go to: https://github.com/adrianhensler/hensler-photography/settings/branches
# Add rule for "main"
```

---

**Next Steps:**
1. Fix CI workflow (30 minutes)
2. Install pre-commit hooks (10 minutes)
3. Enable branch protection (5 minutes)
4. Test: Open a PR and watch CI run automatically!
