# 🔐 GitHub Secrets Setup Guide

## Required Secrets Configuration

Workflows now support **both** authentication methods. Choose one:

### Method 1: Global API Key (Your Current Setup)

Add these 3 secrets to GitHub:
```
https://github.com/qws941/fortinet/settings/secrets/actions
```

**Click "New repository secret" for each:**

1. **CLOUDFLARE_API_KEY**
   - Value: `00ceb252a1a463c9c69a9f5a9f97e5d112bb9` (the key you provided)

2. **CLOUDFLARE_EMAIL** ⚠️ **REQUIRED - You need to add this**
   - Value: Your Cloudflare account email
   - Example: `your-email@example.com`

3. **CLOUDFLARE_ACCOUNT_ID**
   - Get from: https://dash.cloudflare.com
   - Look in the right sidebar after selecting any domain

### Method 2: API Token (More Secure Alternative)

Or use scoped API Token instead:

1. **CLOUDFLARE_API_TOKEN**
   - Get from: https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token" → Use "Edit Cloudflare Workers" template

2. **CLOUDFLARE_ACCOUNT_ID**
   - Same as above

---

## Quick Setup Steps

### Step 1: Navigate to Secrets
```
https://github.com/qws941/fortinet/settings/secrets/actions
```

### Step 2: Add Secrets (Choose your method)

**Using Global Key:**
```
Secret Name: CLOUDFLARE_API_KEY
Value: 00ceb252a1a463c9c69a9f5a9f97e5d112bb9

Secret Name: CLOUDFLARE_EMAIL
Value: [YOUR EMAIL HERE]

Secret Name: CLOUDFLARE_ACCOUNT_ID
Value: [YOUR ACCOUNT ID]
```

**Or using API Token:**
```
Secret Name: CLOUDFLARE_API_TOKEN
Value: [YOUR TOKEN]

Secret Name: CLOUDFLARE_ACCOUNT_ID
Value: [YOUR ACCOUNT ID]
```

### Step 3: Test Deployment

After adding secrets:
```bash
# Option A: Push to trigger auto-deploy
git push origin master

# Option B: Manual deploy via GitHub Actions
# Go to: https://github.com/qws941/fortinet/actions
# → "Manual Deploy to Cloudflare" → "Run workflow"
```

### Step 4: Verify
```bash
curl https://fortinet.jclee.me/api/health
```

---

## ⚠️ Security Reminders

1. **NEVER share API keys in chat, email, or code**
2. **Rotate the key you shared** (it was exposed in chat):
   - Go to: https://dash.cloudflare.com/profile/api-tokens
   - Scroll to "API Keys" → Click "Roll" next to Global API Key

3. **Consider switching to API Token** (more secure):
   - Scoped permissions (Workers only)
   - Can be revoked individually
   - Doesn't grant full account access

---

## Troubleshooting

### "Authentication error"
- Check that secret names match exactly (case-sensitive)
- Ensure CLOUDFLARE_EMAIL is set (required for Global Key)

### "Account ID not found"
- Get Account ID from Cloudflare dashboard sidebar
- Must be hex string (e.g., `abc123def456...`)

### "Insufficient permissions"
- If using API Token: regenerate with "Edit Cloudflare Workers" template
- If using Global Key: ensure email matches your account

---

## What's Next?

After secrets are configured:
1. ✅ Workflows will auto-deploy on push to `master`
2. ✅ Manual deployments available via GitHub Actions
3. ✅ Check deployment status in Actions tab
4. ✅ Verify at https://fortinet.jclee.me/api/health
