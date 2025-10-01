# Session Alias Guide - Short Names

## 🎯 Overview

Use **short names** instead of full `claude-*` session names:

```bash
# Old way ❌
ts-ipc send claude-blacklist claude-manager 'command'

# New way ✅
ts-ipc send blacklist manager 'command'
```

## 📋 Available Aliases

| Short Name | Full Session Name | Status |
|------------|------------------|---------|
| `blacklist` | `claude-blacklist` | ✅ Active |
| `manager` | `claude-manager` | ✅ Active |
| `planka` | `claude-planka` | ✅ Active |
| `fortinet` | `claude-fortinet` | ✅ Active |
| `propose` | `claude-propose` | ✅ Active |
| `splunk` | `claude-splunk` | ✅ Active |
| `mpc` | `claude-mpc` | ✅ Active |

## 🚀 Usage Examples

### TS-IPC (Inter-Session Communication)

```bash
# Send message
ts-ipc send blacklist manager 'docker ps' command

# Subscribe to events
ts-ipc subscribe manager deployment notify

# Publish event
ts-ipc publish blacklist deployment 'v1.2.3'

# Create workflow
ts-ipc workflow deploy \
  'blacklist:npm run build' \
  'manager:docker-compose up -d'

# Execute workflow
ts-ipc run deploy
```

### TS-BG (Background Tasks)

```bash
# Label session (already supports short names!)
ts-bg label blacklist 'backend,production'

# Search by label
ts-bg search production

# Start dev server
ts-bg dev blacklist

# List tasks
ts-bg list blacklist
```

### TS (Session Manager)

```bash
# Works with both!
ts blacklist          # Opens claude-blacklist
ts claude-blacklist   # Also works
```

## 🔧 How It Works

The alias system automatically:
1. Checks if input is a full session name
2. Looks up alias in `~/.config/ts/aliases.json`
3. Falls back to `claude-` prefix if needed

**Resolution Order**:
1. Exact match: `claude-blacklist` → `claude-blacklist`
2. Alias lookup: `blacklist` → `claude-blacklist`
3. Prefix try: `blacklist` → `claude-blacklist`

## 📊 Alias Database

Location: `~/.config/ts/aliases.json`

```json
{
  "aliases": {
    "blacklist": "claude-blacklist",
    "manager": "claude-manager",
    "planka": "claude-planka",
    "fortinet": "claude-fortinet",
    "propose": "claude-propose",
    "splunk": "claude-splunk",
    "mpc": "claude-mpc"
  }
}
```

## 🎨 Real-World Examples

### Example 1: Deployment Pipeline

```bash
# Setup
ts-ipc subscribe manager deployment notify

# Deploy blacklist → notify manager
ts-ipc publish blacklist deployment 'Deployed v1.2.3'

# Create full pipeline
ts-ipc workflow deploy-full \
  'blacklist:npm run build' \
  'blacklist:npm test' \
  'manager:docker-compose pull' \
  'manager:docker-compose up -d'

# Execute
ts-ipc run deploy-full
```

### Example 2: Multi-Service Health Check

```bash
# Check all backend services
for service in blacklist manager fortinet; do
  ts-ipc send monitoring "$service" 'curl localhost/health' command
done
```

### Example 3: Label-Based Operations

```bash
# Label with short names
ts-bg label blacklist 'backend,api,prod'
ts-bg label manager 'backend,admin,prod'
ts-bg label planka 'frontend,ui,prod'

# Search and operate
for session in $(ts-bg search prod | awk '{print $2}'); do
  # Extract short name (remove claude- prefix)
  short_name=${session#claude-}
  echo "Checking $short_name..."
  ts-ipc send monitoring "$short_name" 'systemctl status' command
done
```

## 🛠️ Management Commands

### View Aliases

```bash
/home/jclee/app/tmux/ts-alias.sh show
```

Output:
```
═══════════════════════════════════════════════════
           Session Aliases
═══════════════════════════════════════════════════
  ✓ blacklist → claude-blacklist
  ✓ manager → claude-manager
  ✓ planka → claude-planka
  ...
```

### Auto-Update Aliases

```bash
# Updates aliases for all active sessions
/home/jclee/app/tmux/ts-alias.sh auto
```

### Manual Resolution

```bash
# Test alias resolution
/home/jclee/app/tmux/ts-alias.sh resolve blacklist
# Output: claude-blacklist
```

## 📝 Best Practices

1. **Use short names everywhere**
   ```bash
   # Good ✅
   ts-ipc send blacklist manager 'command'

   # Works but verbose ❌
   ts-ipc send claude-blacklist claude-manager 'command'
   ```

2. **Consistent naming in scripts**
   ```bash
   # Good ✅
   SERVICES=("blacklist" "manager" "planka")
   for svc in "${SERVICES[@]}"; do
     ts-ipc send monitoring "$svc" 'status' command
   done
   ```

3. **Documentation clarity**
   - Use short names in examples
   - Mention full names in reference docs

## 🔍 Troubleshooting

### Issue: Alias not resolving

```bash
# Check if alias exists
cat ~/.config/ts/aliases.json | jq '.aliases'

# Re-generate aliases
/home/jclee/app/tmux/ts-alias.sh auto

# Test resolution
source ~/.config/ts/aliases.sh
resolve_session_name blacklist
```

### Issue: Session not found

```bash
# List all sessions
ts list

# Check socket exists
ls -la /home/jclee/.tmux/sockets/ | grep blacklist
```

## 🚀 Future Enhancements

Planned features:
- [ ] Custom alias creation (not just auto-generated)
- [ ] Alias groups (e.g., `@production` = all prod sessions)
- [ ] Alias history and suggestions
- [ ] Cross-machine alias sync

## 📊 Benefits

**Before** (full names):
```bash
ts-ipc send claude-blacklist claude-manager 'docker ps' command
ts-bg label claude-blacklist 'backend,production'
ts-ipc publish claude-blacklist deployment 'v1.2.3'
```

**After** (short names):
```bash
ts-ipc send blacklist manager 'docker ps' command
ts-bg label blacklist 'backend,production'
ts-ipc publish blacklist deployment 'v1.2.3'
```

**Savings**:
- 50% fewer characters typed
- Cleaner, more readable commands
- Faster workflow execution

---

**Status**: ✅ Active for all commands
**Supported**: `ts`, `ts-bg`, `ts-ipc`
**Auto-updates**: On session changes
**Location**: `~/.config/ts/aliases.json`
