# 🚀 Quick Start Guide

## ✅ You're Almost Ready!

All code is written and tested. Here's what to do next:

### 1. Setup Slack App (5 minutes)

```bash
# 1. Visit https://api.slack.com/apps
# 2. Click "Create New App" → "From scratch"
# 3. Name: "Tmux Bridge", select your workspace
```

**Enable Socket Mode:**
- Settings → Socket Mode → Enable
- Generate token with `connections:write` scope
- Copy the **App Token** (starts with `xapp-`)

**Add Bot Scopes:**
- OAuth & Permissions → Add scopes:
  - `commands`
  - `chat:write`
  - `app_mentions:read`

**Create Slash Command:**
- Slash Commands → Create:
  - Command: `/tmux`
  - Description: "Control tmux sessions"

**Install to Workspace:**
- Install App → Click "Install"
- Copy the **Bot Token** (starts with `xoxb-`)
- Copy **Signing Secret** (in Basic Information)

### 2. Configure Environment

```bash
cd /home/jclee/app/tmux/slack-tmux-bridge

# Create .env file
cat > .env << 'EOF'
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_SIGNING_SECRET=your-secret-here
SLACK_APP_TOKEN=xapp-your-token-here
PORT=3000
WS_PORT=3001
TMUX_SOCKET_DIR=/home/jclee/.tmux/sockets
EOF

# Replace with your actual tokens!
nano .env
```

### 3. Start Server

```bash
# Option 1: Development mode (auto-reload)
npm run dev

# Option 2: Production mode
npm start

# Option 3: Docker
npm run docker:up
```

### 4. Test It!

**Test WebSocket (no Slack needed):**
```bash
# Open in browser
xdg-open test-client.html

# Or run automated test
npm test
```

**Test Slack Commands:**
```
/tmux list
/tmux create myproject
/tmux exec myproject echo "Hello!"
/tmux output myproject
```

## 📊 What You Get

### Slack Commands
| Command | What It Does |
|---------|--------------|
| `/tmux list` | Show all sessions |
| `/tmux create <name>` | Create new session |
| `/tmux exec <name> <cmd>` | Run command |
| `/tmux output <name>` | Get output |
| `/tmux kill <name>` | Kill session |
| `/tmux help` | Show help |

### WebSocket API
```javascript
const ws = new WebSocket('ws://localhost:3001');

// Subscribe to session
ws.send(JSON.stringify({
  action: 'subscribe',
  session: 'myproject'
}));

// Execute command
ws.send(JSON.stringify({
  action: 'exec',
  session: 'myproject',
  command: 'npm start'
}));
```

### Tmux Shortcuts
- **F3** - Switch sessions
- **Ctrl+a |** - Split horizontal
- **Ctrl+a -** - Split vertical

## 🐛 Troubleshooting

**Bot not responding?**
- Check Socket Mode is enabled
- Verify bot is installed to workspace
- Check logs: `npm run docker:logs`

**WebSocket fails?**
- Server running? `ps aux | grep node`
- Port 3001 open? `ss -tlnp | grep 3001`

**Tests fail?**
- Tmux installed? `tmux -V`
- Socket dir exists? `ls ~/.tmux/sockets`

## 📚 Next Steps

- Read [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed docs
- Check [README.md](README.md) for architecture
- Add Grafana integration (logger already included!)

## 💡 Pro Tips

1. **Create test session first:**
   ```bash
   ts create test-websocket
   ```

2. **Open test client:**
   ```bash
   python3 -m http.server 8000 &
   xdg-open http://localhost:8000/test-client.html
   ```

3. **Monitor logs:**
   ```bash
   npm start | tee slack-tmux-bridge.log
   ```

4. **Deploy with Docker:**
   ```bash
   npm run docker:up
   npm run docker:logs -f
   ```

---

## ✨ Features

✅ **WebSocket** - Real-time terminal streaming
✅ **Slack Bot** - Control via slash commands
✅ **Tmux API** - Full session management
✅ **Tests** - Automated test suite
✅ **Docker** - Container-ready
✅ **Grafana** - Logging integration
✅ **F3 Shortcut** - Quick session switch

---

**Ready to go!** 🎉

Just add your Slack tokens and run `npm start`!
