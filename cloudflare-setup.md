# Cloudflare Deployment Setup

## Quick Start

### 1. Install Wrangler
```bash
npm install -g wrangler
wrangler login
```

### 2. Create Resources
```bash
# D1 Database
wrangler d1 create fortinet_db

# R2 Storage
wrangler r2 bucket create fortinet-storage

# KV Namespace
wrangler kv:namespace create CONFIG
```

### 3. Update wrangler.toml
Add the IDs from resource creation to wrangler.toml

### 4. Set Secrets
```bash
echo "your-key" | wrangler secret put FORTIMANAGER_API_KEY
echo "your-key" | wrangler secret put SECRET_KEY
```

### 5. Deploy
```bash
wrangler deploy --env production
```

## GitHub Secrets Required
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
- FORTIMANAGER_API_KEY
- FORTIGATE_API_KEY
- SECRET_KEY

## Verification
```bash
curl https://fortinet.jclee.me/api/health
```
