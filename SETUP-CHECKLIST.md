# 🎯 GitHub Secrets Setup Checklist

## Your Configuration Details

### ✅ Information Collected:
- **API Key:** `00ceb252a1a463c9c69a9f5a9f97e5d112bb9`
- **Email:** `qws941@kakao.com`
- **Account ID:** ⚠️ **STILL NEEDED**

---

## 🚀 Complete Setup in 3 Steps

### Step 1: Get Your Cloudflare Account ID

1. Go to: **https://dash.cloudflare.com**
2. Look at the **RIGHT SIDEBAR**
3. Find: `Account ID: [32-character string]`
4. Copy the full 32-character hex string
   - Example format: `abc123def456789012345678901234567`
   - Must be exactly 32 characters (0-9, a-f)

### Step 2: Add GitHub Secrets

Go to: **https://github.com/qws941/fortinet/settings/secrets/actions**

Click "New repository secret" **3 times** to add these:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Secret #1:
  Name: CLOUDFLARE_API_KEY
  Value: 00ceb252a1a463c9c69a9f5a9f97e5d112bb9
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Secret #2:
  Name: CLOUDFLARE_EMAIL
  Value: qws941@kakao.com
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Secret #3:
  Name: CLOUDFLARE_ACCOUNT_ID
  Value: [PASTE YOUR 32-CHAR ACCOUNT ID HERE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 3: Deploy & Verify

**Option A: Auto-deploy** (push any change)
```bash
cd /home/jclee/app/fortinet
echo "# Test" >> README.md
git add README.md
git commit -m "test: trigger deployment"
git push origin master
```

**Option B: Manual deploy**
- Go to: https://github.com/qws941/fortinet/actions
- Click "Manual Deploy to Cloudflare"
- Click "Run workflow" → Select "production" → "Run workflow"

**Verify:**
```bash
# Wait 1-2 minutes after deployment, then:
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

## 🔒 Security Reminder

After successful deployment, **rotate your API key**:

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Scroll to "API Keys" section
3. Click "Roll" next to "Global API Key"
4. Update the `CLOUDFLARE_API_KEY` secret in GitHub with the new value

---

## ✅ Checklist

- [x] Cloudflare API Key obtained
- [x] Cloudflare email confirmed
- [ ] Get Cloudflare Account ID from dashboard
- [ ] Add all 3 secrets to GitHub
- [ ] Test deployment
- [ ] Verify at https://fortinet.jclee.me/api/health
- [ ] Rotate API key for security

---

## 📞 Next Steps

**Tell me when you have:**
1. Your Account ID from the Cloudflare dashboard
2. Confirmation that you've added all 3 secrets to GitHub

Then I'll help you trigger and verify the deployment! 🚀
