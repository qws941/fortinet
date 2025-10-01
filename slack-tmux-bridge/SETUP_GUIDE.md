# Slack Tmux Bridge - Setup Guide

## 🎯 Quick Start

### 1. Install Dependencies

```bash
cd /home/jclee/app/tmux/slack-tmux-bridge
npm install
```

### 2. Create Slack App

#### Step 1: Go to Slack API
https://api.slack.com/apps → **Create New App** → **From scratch**

#### Step 2: Basic Information
- App Name: `Tmux Bridge`
- Workspace: Select your workspace

#### Step 3: Enable Socket Mode
- Settings → Socket Mode → **Enable Socket Mode**
- Generate App-Level Token with `connections:write` scope
- Copy **App Token** (`xapp-...`)

#### Step 4: Add Bot Scopes
- OAuth & Permissions → Bot Token Scopes:
  - `commands` - For slash commands
  - `chat:write` - To send messages
  - `app_mentions:read` - To read mentions

#### Step 5: Create Slash Command
- Slash Commands → Create New Command:
  - Command: `/tmux`
  - Request URL: (leave blank for Socket Mode)
  - Short Description: `Control tmux sessions`
  - Usage Hint: `[list|create|exec|kill|output] [args]`

#### Step 6: Install to Workspace
- Install App → **Install to Workspace**
- Copy **Bot User OAuth Token** (`xoxb-...`)

#### Step 7: Get Signing Secret
- Basic Information → App Credentials
- Copy **Signing Secret**

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your tokens
nano .env
```

Fill in:
```env
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_APP_TOKEN=xapp-your-app-token-here
```

### 4. Run Server

```bash
# Development mode (auto-reload)
npm run dev

# Production mode
npm start
```

### 5. Test WebSocket Connection

Open `test-client.html` in your browser:
```bash
# Open in default browser
xdg-open test-client.html

# Or serve with Python
python3 -m http.server 8000
# Then visit http://localhost:8000/test-client.html
```

## 🚀 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📱 Using Slack Commands

### List Sessions
```
/tmux list
```

### Create Session
```
/tmux create myproject
```

### Execute Command
```
/tmux exec myproject ls -la
```

### Get Output
```
/tmux output myproject 50
```

### Kill Session
```
/tmux kill myproject
```

### Get Help
```
/tmux help
```

## 🔌 WebSocket API Examples

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:3001');

ws.onopen = () => {
  // Subscribe to session output
  ws.send(JSON.stringify({
    action: 'subscribe',
    session: 'myproject'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};

// Execute command
ws.send(JSON.stringify({
  action: 'exec',
  session: 'myproject',
  command: 'npm run dev'
}));

// Send Ctrl+C
ws.send(JSON.stringify({
  action: 'sendKeys',
  session: 'myproject',
  keys: 'C-c'
}));
```

### Python Client

```python
import websocket
import json

ws = websocket.create_connection('ws://localhost:3001')

# Subscribe
ws.send(json.dumps({
    'action': 'subscribe',
    'session': 'myproject'
}))

# Receive output
while True:
    result = ws.recv()
    data = json.loads(result)
    print(data)
```

## 🔧 Tmux Shortcuts (Added)

| Key | Action |
|-----|--------|
| `F3` | **Switch between sessions** |
| `Ctrl+a` then `|` | Split pane horizontally |
| `Ctrl+a` then `-` | Split pane vertically |
| `Alt+Arrow` | Switch panes |
| `Shift+Arrow` | Switch windows |
| `Ctrl+Arrow` | Resize panes |

## 🐛 Troubleshooting

### Slack Bot not responding
1. Check Socket Mode is enabled
2. Verify App Token has `connections:write` scope
3. Check bot is installed to workspace
4. View server logs for errors

### WebSocket connection fails
1. Check server is running
2. Verify port 3001 is not blocked
3. Check firewall settings

### Tmux sessions not found
1. Verify socket directory: `/home/jclee/.tmux/sockets`
2. Check tmux is installed: `tmux -V`
3. List actual sessions: `tmux list-sessions`

## 📊 Architecture

```
┌─────────────────┐
│   Slack App     │
└────────┬────────┘
         │ /tmux commands
         ↓
┌─────────────────┐
│   Slack Bot     │
│   (Socket Mode) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐     ┌──────────────────┐
│  Tmux Wrapper   │────→│  Tmux Sessions   │
└────────┬────────┘     └──────────────────┘
         │
         ↓
┌─────────────────┐
│ WebSocket Server│←──── Real-time clients
└─────────────────┘
```

## 📝 Next Steps

1. Add authentication to WebSocket
2. Implement session sharing permissions
3. Add Grafana metrics integration
4. Create Slack interactive buttons
5. Add session recording/playback

## 📚 Resources

- [Slack Bolt SDK](https://slack.dev/bolt-js/)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Tmux Manual](https://man7.org/linux/man-pages/man1/tmux.1.html)
