# Slack Tmux Bridge

WebSocket + Slack integration for controlling tmux sessions remotely.

## Architecture

```
Slack App
    ↓ (Slash Command: /tmux exec ls -la)
Slack Bot Handler
    ↓
Tmux API Wrapper
    ↓
Tmux Sessions
    ↓ (Output)
WebSocket Server
    ↓
Slack (Response)
```

## Features

- **Slack Commands**: Control tmux via Slack slash commands
- **Real-time Streaming**: WebSocket-based live terminal output
- **Session Management**: Create, list, and destroy tmux sessions
- **Command Execution**: Execute arbitrary commands in tmux
- **Output Capture**: Get command output in real-time

## Setup

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Create new app
3. Enable Socket Mode
4. Add Bot Token Scopes:
   - `commands`
   - `chat:write`
   - `app_mentions:read`
5. Install app to workspace
6. Copy tokens to `.env`

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Slack tokens
```

### 4. Run Server

```bash
npm start
# or for development:
npm run dev
```

## Slack Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/tmux exec <cmd>` | Execute command in tmux | `/tmux exec ls -la` |
| `/tmux list` | List all sessions | `/tmux list` |
| `/tmux create <name>` | Create new session | `/tmux create myproject` |
| `/tmux kill <name>` | Kill session | `/tmux kill myproject` |
| `/tmux output <session>` | Get session output | `/tmux output myproject` |

## WebSocket API

### Connect

```javascript
const ws = new WebSocket('ws://localhost:3001');
```

### Subscribe to Session Output

```javascript
ws.send(JSON.stringify({
  action: 'subscribe',
  session: 'mysession'
}));
```

### Execute Command

```javascript
ws.send(JSON.stringify({
  action: 'exec',
  session: 'mysession',
  command: 'ls -la'
}));
```

## Docker Deployment

```bash
docker-compose up -d
```

## License

MIT
