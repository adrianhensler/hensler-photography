# Git Workflow Best Practices

This document establishes workflow practices to prevent "divergent branches" and lost work.

## What Happened (November 22, 2025)

**Issue**: During PR #4 deployment, production had:
- 1 uncommitted local changes (Caddyfile, docker-compose.yml, etc.)
- 1 unpushed commit (9887fde)
- Meanwhile, GitHub had PR #4 merge commit (35d274a)

**Result**: Git reported "divergent branches" - local and remote histories had split.

**Resolution**: Stashed local changes, reset to origin/main, recovered work as PR #5.

**Lesson**: Work was nearly lost. Let's prevent this.

---

## The Golden Rule

> **Never let production diverge from GitHub main branch.**

If production has commits that GitHub doesn't, or vice versa, we have a problem.

---

## Recommended Workflows

### **Option 1: Feature Branch Workflow** (Best for significant changes)

```bash
# 1. Start from clean main
cd /opt/prod/hensler_photography
git checkout main
git pull origin main

# 2. Create feature branch
git checkout -b feature/my-improvement

# 3. Make changes, test locally
# ... edit files ...
docker compose restart  # if needed

# 4. Commit to branch
git add .
git commit -m "Descriptive message"

# 5. Push branch
git push origin feature/my-improvement

# 6. Create PR on GitHub
gh pr create --title "..." --body "..."

# 7. After PR approved and merged, update production
git checkout main
git pull origin main
docker compose restart
```

**Benefits**:
- ✅ Production stays clean (on main)
- ✅ Work is backed up on GitHub immediately
- ✅ Can review changes before they go live
- ✅ Never lose work

**When to use**: Any non-trivial change (new features, refactoring, optimizations)

---

### **Option 2: Direct Commit to Main** (For tiny fixes only)

```bash
# 1. Make small change
# ... edit file ...

# 2. Commit AND push immediately
git add .
git commit -m "Fix typo in header"
git push origin main

# 3. Restart if needed
docker compose restart
```

**Benefits**:
- ✅ Fast for tiny changes
- ✅ Change is on GitHub immediately

**Risks**:
- ⚠️ If you forget to push, causes divergence
- ⚠️ No review before going live

**When to use**: Only for trivial changes (typos, minor CSS tweaks, config adjustments)

**Rule**: If you commit, you MUST push immediately. Never commit without pushing.

---

### **Option 3: No Commit (Fastest for experiments)**

```bash
# 1. Make change directly
# ... edit file ...

# 2. Restart to test
docker compose restart

# 3. If it works, commit via Option 1 or 2
# 4. If it doesn't work:
git restore <file>  # Undo changes
```

**Benefits**:
- ✅ Fast experimentation
- ✅ No git history pollution

**Risks**:
- ⚠️ Changes lost if you pull from GitHub
- ⚠️ Can't recover if you break something

**When to use**: Quick tests, debugging, experiments you might throw away

---

## How to Check Status Before Pulling

**Before any `git pull`, always check:**

```bash
# Check for uncommitted changes
git status

# Check for unpushed commits
git log origin/main..HEAD

# If either shows anything, handle it BEFORE pulling!
```

**If you have uncommitted changes:**
- Option A: Commit them (Option 1 or 2 above)
- Option B: Stash them (`git stash`)
- Option C: Discard them (`git restore .`)

**If you have unpushed commits:**
- Option A: Push them (`git push origin main`)
- Option B: Create PR from branch
- Option C: Reset if they're not important

---

## Claude's Improvements

### What Claude Will Do Better:

1. **Check git status before deployments**
   ```bash
   git status
   git log origin/main..HEAD
   ```
   If there are uncommitted/unpushed changes, alert you and ask what to do.

2. **Warn about divergence**
   If `git pull` fails with divergent branches, explain clearly:
   - What's local that's not on GitHub
   - What's on GitHub that's not local
   - Options to resolve (stash, branch, reset)

3. **Always create feature branches for recovered work**
   Like we did with PR #5 - never lose work.

4. **Suggest workflow at start of sessions**
   "Want to create a feature branch for this work?"

5. **Verify production matches GitHub after deployments**
   ```bash
   git status  # Should be clean
   git log --oneline -3  # Should match GitHub
   ```

---

## Your Improvements

### What You Can Do:

1. **Choose a workflow** (Option 1 recommended)
   - Decide: "I'll use feature branches for everything except typos"

2. **Push early and often**
   - If you commit, push immediately
   - Don't let commits sit unpushed for days

3. **Check status before asking Claude to deploy**
   ```bash
   git status  # Clean?
   git log origin/main..HEAD  # Nothing unpushed?
   ```

4. **Tell Claude your workflow preference**
   - "Always create a feature branch"
   - "I want to review before main"

5. **Use meaningful commit messages**
   - Good: "Optimize gallery image serving via direct file_server"
   - Bad: "Fix stuff"

---

## Quick Reference

### ✅ Safe Operations (Never Cause Problems)
- `git status` - Check what's changed
- `git log` - View history
- `git diff` - See changes
- `git stash list` - See stashed work
- `git stash show -p` - View stashed changes

### ⚠️ Operations That Change Things (Use Carefully)
- `git pull` - Can fail if divergent
- `git reset --hard` - Discards local changes permanently
- `git push --force` - Dangerous, avoid
- `git rebase` - Advanced, can cause issues

### 🚨 Emergency Recovery
- Lost uncommitted work: `git reflog` (might recover)
- Lost commits: `git reflog` (definitely recover)
- Divergent branches: Ask Claude before acting

---

## Automation Ideas (Future)

**Git Hooks** - Automatically check/remind:
- Pre-commit: Warn if committing to main (suggest branch)
- Pre-push: Verify tests pass
- Post-merge: Remind to deploy

**Deployment Script** - Safe deployment:
```bash
#!/bin/bash
# deploy.sh
set -e

echo "Checking git status..."
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: Uncommitted changes detected"
    git status
    exit 1
fi

echo "Pulling from GitHub..."
git pull origin main

echo "Restarting containers..."
docker compose restart

echo "✅ Deployment complete"
```

---

## Summary

**The Three Rules**:
1. **Feature branch for everything non-trivial**
2. **If you commit, push immediately**
3. **Check status before pulling**

Follow these, and we'll never have divergent branches again.

---

**Last updated**: November 22, 2025
**Next review**: After next deployment issue (hopefully never!)
