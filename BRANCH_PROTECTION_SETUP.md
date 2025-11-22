# Branch Protection Setup Guide

## Why Branch Protection?

**Without it:**
- Anyone can push broken code to main
- Bugs reach production without review
- No safety net

**With it:**
- ✅ All changes go through Pull Requests
- ✅ Tests must pass before merge
- ✅ Code review required
- ✅ Can't accidentally break main

---

## Setup Instructions (5 minutes)

### Step 1: Go to Branch Settings

Visit: https://github.com/adrianhensler/hensler-photography/settings/branches

Or navigate:
1. Go to your repository
2. Click "Settings" (top menu)
3. Click "Branches" (left sidebar)

---

### Step 2: Add Protection Rule

Click: **"Add branch protection rule"**

---

### Step 3: Configure Protection

**Branch name pattern:**
```
main
```

**Enable these settings:**

#### Protect matching branches:
- [x] **Require a pull request before merging**
  - Require approvals: 0 (or 1 if you want self-review)
  - Dismiss stale pull request approvals when new commits are pushed

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - **Status checks that are required:**
    - `test` (this is the "Automated Testing" workflow)

- [x] **Require conversation resolution before merging**
  - All PR comments must be resolved

- [ ] Require signed commits (optional, but good for security)

- [x] **Do not allow bypassing the above settings**
  - Even admins (you) must follow the rules

#### Rules applied to everyone including administrators:
- [x] **Include administrators**
  - You can't bypass your own rules

---

### Step 4: Save

Click: **"Create"** (or **"Save changes"** if editing existing rule)

---

## What This Means

### Before Branch Protection:
```bash
git checkout main
# Make changes
git commit -m "Quick fix"
git push origin main  # ← Goes straight to production!
```

### After Branch Protection:
```bash
git checkout -b fix/my-bug
# Make changes
git commit -m "Fix bug"
git push origin fix/my-bug

# Create PR on GitHub
gh pr create

# CI runs tests automatically
# If tests pass → can merge
# If tests fail → can't merge until fixed
```

---

## Testing Branch Protection

After setting it up, try to push to main:

```bash
cd /opt/prod/hensler_photography
git checkout main

# Try to push (should fail)
echo "test" >> README.md
git add README.md
git commit -m "Test branch protection"
git push origin main
```

**Expected result:**
```
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: error: Changes must be made through a pull request.
```

✅ **If you see this error, branch protection is working!**

Then undo the test:
```bash
git reset HEAD~1
git checkout README.md
```

---

## Emergency: Disabling Branch Protection

If you ever need to bypass (emergencies only):

1. Go to: https://github.com/adrianhensler/hensler-photography/settings/branches
2. Find the `main` rule
3. Click "Delete" (temporarily)
4. Make your emergency change
5. **Re-enable immediately after**

**Better approach:** Use the rollback script instead of disabling protection.

---

## Troubleshooting

### "I can't find the 'test' status check"

The test workflow needs to run at least once. PR #7 should make it available. If not:
1. Wait for PR #7 CI to complete
2. Then come back and add the status check requirement

### "What if I want to push directly in an emergency?"

You have two options:
1. Temporarily disable branch protection (not recommended)
2. Use the emergency rollback procedure (better)

For rollback, see: DEPLOYMENT_STRATEGY.md

---

## Success Criteria

Branch protection is working when:
- ✅ Can't `git push origin main` directly
- ✅ Must create PR to make changes
- ✅ CI runs automatically on every PR
- ✅ Can only merge if tests pass
- ✅ Green checkmark on main branch

---

**This is the single most important safety measure.** It prevents 90% of "oops, I broke production" moments.

Set it up now, thank yourself later. 🛡️
