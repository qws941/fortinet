# Cloudflare Auto-Deployment Guide

## ✅ Setup Complete

Auto-deployment to Cloudflare Workers is now configured with two workflows:

### 1. Automatic Deployment (on push)
**File:** `.github/workflows/cloudflare-deploy.yml`

Triggers automatically when pushing to:
- `main` branch
- `master` branch
- `develop` branch

Only when these paths change:
- `src/**`
- `wrangler.toml`
- `requirements.txt`
- `.github/workflows/cloudflare-deploy.yml`

### 2. Manual Deployment
**File:** `.github/workflows/manual-deploy.yml`

Deploy manually via GitHub Actions:
1. Go to: https://github.com/qws941/fortinet/actions
2. Select "Manual Deploy to Cloudflare"
3. Click "Run workflow"
4. Choose environment: `production` or `staging`
5. Click "Run workflow" button

## 🔐 Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

```bash
# Go to: https://github.com/qws941/fortinet/settings/secrets/actions

Required secrets:
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
```

### Getting Cloudflare Credentials

1. **API Token:**
   - Go to https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token"
   - Use "Edit Cloudflare Workers" template
   - Copy the token

2. **Account ID:**
   - Go to https://dash.cloudflare.com
   - Select your domain
   - Copy Account ID from the right sidebar

## 🚀 Deploy Now

### Option 1: Push to master
```bash
git add .
git commit -m "feat: auto-deploy setup"
git push origin master
```

### Option 2: Manual deployment
```bash
# Via GitHub web interface
# Go to Actions tab → Manual Deploy → Run workflow

# Or using GitHub CLI
gh workflow run manual-deploy.yml -f environment=production
```

## 🌍 Deployment URLs

- **Production:** https://fortinet.jclee.me/api/health
- **Staging:** https://fortinet-staging.jclee.me/api/health

## 📋 Next Steps

1. Add GitHub secrets (if not already configured)
2. Update `wrangler.toml` with actual resource IDs:
   - KV namespace ID
   - D1 database ID
   - R2 bucket name

3. Create Cloudflare resources (if needed):
```bash
# D1 Database
wrangler d1 create fortinet_db

# R2 Storage
wrangler r2 bucket create fortinet-storage

# KV Namespace
wrangler kv:namespace create CONFIG
```

4. Set worker secrets (if needed):
```bash
echo "your-key" | wrangler secret put FORTIMANAGER_API_KEY
echo "your-key" | wrangler secret put SECRET_KEY
```

## ✅ Verification

After deployment:
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
