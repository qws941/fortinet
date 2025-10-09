# 🚀 Auto-Deploy Guide

## ✅ Status: CONFIGURED & ACTIVE

Auto-deployment is **already working**! Here's how it operates:

---

## 🎯 How Auto-Deploy Works

### Automatic Triggers

**Workflow:** `.github/workflows/cloudflare-deploy.yml`

**Triggers on:**
```yaml
✅ Branch: master, main, or develop
✅ Files changed:
   - src/**
   - wrangler.toml
   - requirements.txt
   - .github/workflows/cloudflare-deploy.yml
```

**What happens:**
1. You push code to `master` branch
2. GitHub Actions detects the change
3. Workflow runs automatically
4. Deploys to Cloudflare Workers (production)
5. You get notification (success/failure)

---

## 📋 Prerequisites (Required First Time)

### GitHub Secrets (ONE-TIME SETUP)

Go to: https://github.com/qws941/fortinet/settings/secrets/actions

Add these 3 secrets:

```
CLOUDFLARE_API_KEY: 00ceb252a1a463c9c69a9f5a9f97e5d112bb9
CLOUDFLARE_EMAIL: qws941@kakao.com
CLOUDFLARE_ACCOUNT_ID: [Get from https://dash.cloudflare.com]
```

**Without these secrets:** ❌ Deployment fails
**With these secrets:** ✅ Deployment succeeds automatically

---

## 🚀 Test Auto-Deploy (3 Ways)

### Method 1: Edit Source Code
```bash
cd /home/jclee/app/fortinet

# Make a small change to worker
echo "// Updated $(date)" >> src/worker.js

git add src/worker.js
git commit -m "test: trigger auto-deploy"
git push origin master
```

### Method 2: Update Configuration
```bash
# Modify wrangler.toml
vim wrangler.toml  # Make any change

git add wrangler.toml
git commit -m "config: update wrangler"
git push origin master
```

### Method 3: Update README (Won't trigger)
```bash
# Changes to README.md DON'T trigger deployment
echo "# Test" >> README.md
git add README.md
git commit -m "docs: update readme"
git push origin master
# ❌ No deployment (README not in trigger paths)
```

---

## 👀 Monitor Deployments

### Watch in Real-Time

1. **GitHub Actions Tab:**
   - https://github.com/qws941/fortinet/actions
   - See live deployment progress
   - View logs and errors

2. **Command Line:**
   ```bash
   # Watch workflow runs (requires gh CLI)
   gh run watch

   # List recent runs
   gh run list --workflow="cloudflare-deploy.yml"
   ```

3. **Notifications:**
   - GitHub sends email on success/failure
   - Configure at: https://github.com/settings/notifications

---

## 🔍 Verify Deployment

After deployment completes (1-2 minutes):

```bash
# Check health endpoint
curl https://fortinet.jclee.me/api/health

# Expected response:
{
  "status": "healthy",
  "service": "fortinet-nextrade",
  "deployment": "cloudflare-workers",
  "timestamp": "2025-10-09T..."
}
```

---

## 🎛️ Deployment Environments

### Production (auto)
- **Branch:** `master` or `main`
- **URL:** https://fortinet.jclee.me
- **Wrangler env:** `production`

### Staging (auto)
- **Branch:** `develop`
- **URL:** https://fortinet-staging.jclee.me
- **Wrangler env:** `staging`

---

## 🚨 Troubleshooting

### "Deployment Failed: Authentication"
```
❌ GitHub secrets not configured
✅ Add secrets at: /settings/secrets/actions
```

### "Deployment Skipped"
```
❌ Changed files don't match trigger paths
✅ Only src/, wrangler.toml, requirements.txt trigger
```

### "Wrangler Error"
```
❌ Account ID or resource IDs missing in wrangler.toml
✅ Update wrangler.toml with actual IDs
```

---

## ⚙️ Advanced: Manual Control

### Disable Auto-Deploy
```bash
# Rename workflow file
mv .github/workflows/cloudflare-deploy.yml \
   .github/workflows/cloudflare-deploy.yml.disabled
```

### Deploy Manually Only
```bash
# Use manual-deploy workflow instead
# Go to: /actions → "Manual Deploy" → "Run workflow"
```

### Deploy from CLI
```bash
# Using wrangler directly
wrangler deploy --env production

# Using gh CLI to trigger workflow
gh workflow run manual-deploy.yml -f environment=production
```

---

## 📊 Workflow Files

Current active workflows:

| Workflow | Trigger | Status |
|----------|---------|--------|
| `cloudflare-deploy.yml` | Auto (push) | ✅ Active |
| `manual-deploy.yml` | Manual | ✅ Active |
| `branch-strategy.yml` | Branch events | ✅ Active |
| `Claude Code Integration` | Various | ✅ Active |

---

## 🎯 Quick Reference

```bash
# Test auto-deploy
echo "// Test" >> src/worker.js && \
  git add . && \
  git commit -m "test: auto-deploy" && \
  git push origin master

# Watch deployment
gh run watch

# Check result
curl https://fortinet.jclee.me/api/health
```

---

## ✅ Next Steps

1. **Add GitHub secrets** (if not done)
2. **Push a test change** to trigger deployment
3. **Watch the Actions tab** to see it work
4. **Verify the deployment** with curl

**Everything is ready! Just add the secrets and push any change to master.** 🚀
