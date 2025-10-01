#!/usr/bin/env node
/**
 * Tmux WebSocket Management Server
 * Real-time tmux session monitoring and control via WebSocket
 */

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.PORT || 3030;
const TS_CONFIG = path.join(process.env.HOME, '.config/ts/sessions.db');

// Serve static files
app.use(express.static('public'));
app.use(express.json());

// Utility: Execute shell command and return promise
function executeCommand(cmd) {
  return new Promise((resolve, reject) => {
    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        reject({ error: error.message, stderr });
      } else {
        resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
      }
    });
  });
}

// Get all tmux sessions
async function getTmuxSessions() {
  try {
    const { stdout } = await executeCommand('tmux ls -F "#{session_name}|#{session_windows}|#{session_attached}|#{session_created}" 2>/dev/null || echo ""');

    if (!stdout) return [];

    return stdout.split('\n').filter(Boolean).map(line => {
      const [name, windows, attached, created] = line.split('|');
      return {
        name,
        windows: parseInt(windows),
        attached: parseInt(attached),
        created: new Date(parseInt(created) * 1000).toISOString(),
        status: parseInt(attached) > 0 ? 'attached' : 'detached'
      };
    });
  } catch (err) {
    console.error('Error getting tmux sessions:', err);
    return [];
  }
}

// Get TS database sessions
async function getTsSessions() {
  try {
    if (!fs.existsSync(TS_CONFIG)) return [];
    const data = fs.readFileSync(TS_CONFIG, 'utf8');
    const db = JSON.parse(data);
    return db.sessions || [];
  } catch (err) {
    console.error('Error reading TS database:', err);
    return [];
  }
}

// Merge tmux sessions with TS metadata
async function getAllSessions() {
  const [tmuxSessions, tsSessions] = await Promise.all([
    getTmuxSessions(),
    getTsSessions()
  ]);

  // Create a map for quick lookup
  const tsMap = new Map(tsSessions.map(s => [s.name, s]));

  return tmuxSessions.map(tmux => ({
    ...tmux,
    metadata: tsMap.get(tmux.name) || {},
    hasMetadata: tsMap.has(tmux.name)
  }));
}

// WebSocket connection handler
wss.on('connection', (ws) => {
  console.log('Client connected');

  // Send initial session list
  getAllSessions().then(sessions => {
    ws.send(JSON.stringify({
      type: 'sessions',
      data: sessions,
      timestamp: new Date().toISOString()
    }));
  });

  // Handle incoming messages
  ws.on('message', async (message) => {
    try {
      const msg = JSON.parse(message);
      console.log('Received:', msg);

      switch (msg.action) {
        case 'list':
          const sessions = await getAllSessions();
          ws.send(JSON.stringify({
            type: 'sessions',
            data: sessions,
            timestamp: new Date().toISOString()
          }));
          break;

        case 'create':
          const { name, path: sessionPath } = msg;
          if (!name) {
            ws.send(JSON.stringify({ type: 'error', message: 'Session name required' }));
            break;
          }

          const createCmd = sessionPath
            ? `ts create ${name} ${sessionPath}`
            : `ts create ${name}`;

          try {
            await executeCommand(createCmd);
            ws.send(JSON.stringify({
              type: 'success',
              message: `Session '${name}' created`,
              action: 'create'
            }));

            // Send updated session list
            const updatedSessions = await getAllSessions();
            ws.send(JSON.stringify({
              type: 'sessions',
              data: updatedSessions,
              timestamp: new Date().toISOString()
            }));
          } catch (err) {
            ws.send(JSON.stringify({
              type: 'error',
              message: `Failed to create session: ${err.error}`
            }));
          }
          break;

        case 'kill':
          const { sessionName } = msg;
          if (!sessionName) {
            ws.send(JSON.stringify({ type: 'error', message: 'Session name required' }));
            break;
          }

          try {
            await executeCommand(`ts kill ${sessionName}`);
            ws.send(JSON.stringify({
              type: 'success',
              message: `Session '${sessionName}' killed`,
              action: 'kill'
            }));

            // Send updated session list
            const updatedSessions = await getAllSessions();
            ws.send(JSON.stringify({
              type: 'sessions',
              data: updatedSessions,
              timestamp: new Date().toISOString()
            }));
          } catch (err) {
            ws.send(JSON.stringify({
              type: 'error',
              message: `Failed to kill session: ${err.error}`
            }));
          }
          break;

        case 'clean':
          try {
            await executeCommand('ts clean');
            ws.send(JSON.stringify({
              type: 'success',
              message: 'All sessions cleaned',
              action: 'clean'
            }));

            // Send updated session list
            const updatedSessions = await getAllSessions();
            ws.send(JSON.stringify({
              type: 'sessions',
              data: updatedSessions,
              timestamp: new Date().toISOString()
            }));
          } catch (err) {
            ws.send(JSON.stringify({
              type: 'error',
              message: `Failed to clean sessions: ${err.error}`
            }));
          }
          break;

        case 'sync':
          try {
            await executeCommand('ts sync');
            ws.send(JSON.stringify({
              type: 'success',
              message: 'Database synced with tmux',
              action: 'sync'
            }));

            // Send updated session list
            const updatedSessions = await getAllSessions();
            ws.send(JSON.stringify({
              type: 'sessions',
              data: updatedSessions,
              timestamp: new Date().toISOString()
            }));
          } catch (err) {
            ws.send(JSON.stringify({
              type: 'error',
              message: `Failed to sync: ${err.error}`
            }));
          }
          break;

        default:
          ws.send(JSON.stringify({
            type: 'error',
            message: `Unknown action: ${msg.action}`
          }));
      }
    } catch (err) {
      console.error('Error processing message:', err);
      ws.send(JSON.stringify({
        type: 'error',
        message: 'Invalid message format'
      }));
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
  });
});

// Broadcast session updates every 5 seconds
setInterval(async () => {
  const sessions = await getAllSessions();
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify({
        type: 'sessions',
        data: sessions,
        timestamp: new Date().toISOString()
      }));
    }
  });
}, 5000);

// REST API endpoints
app.get('/api/sessions', async (req, res) => {
  try {
    const sessions = await getAllSessions();
    res.json({ success: true, data: sessions });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

app.post('/api/sessions/create', async (req, res) => {
  const { name, path } = req.body;
  if (!name) {
    return res.status(400).json({ success: false, error: 'Session name required' });
  }

  try {
    const cmd = path ? `ts create ${name} ${path}` : `ts create ${name}`;
    await executeCommand(cmd);
    res.json({ success: true, message: `Session '${name}' created` });
  } catch (err) {
    res.status(500).json({ success: false, error: err.error });
  }
});

app.delete('/api/sessions/:name', async (req, res) => {
  const { name } = req.params;

  try {
    await executeCommand(`ts kill ${name}`);
    res.json({ success: true, message: `Session '${name}' killed` });
  } catch (err) {
    res.status(500).json({ success: false, error: err.error });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    websocket: wss.clients.size
  });
});

// Start server
server.listen(PORT, () => {
  console.log(`Tmux WebSocket Server running on port ${PORT}`);
  console.log(`WebSocket: ws://localhost:${PORT}`);
  console.log(`REST API: http://localhost:${PORT}/api`);
  console.log(`Web UI: http://localhost:${PORT}`);
});
