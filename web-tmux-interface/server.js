const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { exec, spawn } = require('child_process');
const path = require('path');
const cors = require('cors');

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Utility: Execute shell command
function execPromise(command) {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error && !stdout) {
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
    const { stdout } = await execPromise('tmux ls -F "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}" 2>&1');
    const lines = stdout.split('\n').filter(l => l.trim());

    return lines.map(line => {
      const [name, windows, created, attached] = line.split('|');
      return {
        name,
        windows: parseInt(windows) || 0,
        created: new Date(parseInt(created) * 1000).toISOString(),
        attached: attached === '1',
        socket: `/home/jclee/.tmux/sockets/${name}`
      };
    });
  } catch (error) {
    if (error.stdout && error.stdout.includes('no server running')) {
      return [];
    }
    throw error;
  }
}

// Get session details
async function getSessionDetails(sessionName) {
  try {
    const { stdout } = await execPromise(`tmux list-windows -t ${sessionName} -F "#{window_index}|#{window_name}|#{window_active}|#{window_panes}"`);
    const lines = stdout.split('\n').filter(l => l.trim());

    return lines.map(line => {
      const [index, name, active, panes] = line.split('|');
      return {
        index: parseInt(index),
        name,
        active: active === '1',
        panes: parseInt(panes)
      };
    });
  } catch (error) {
    return [];
  }
}

// REST API Endpoints
app.get('/api/sessions', async (req, res) => {
  try {
    const sessions = await getTmuxSessions();
    res.json({ success: true, sessions });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/sessions/:name', async (req, res) => {
  try {
    const windows = await getSessionDetails(req.params.name);
    res.json({ success: true, windows });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/sessions', async (req, res) => {
  const { name, path } = req.body;
  try {
    const cmd = `tmux new-session -d -s "${name}" -c "${path || '/home/jclee'}"`;
    await execPromise(cmd);
    res.json({ success: true, message: `Session '${name}' created` });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.delete('/api/sessions/:name', async (req, res) => {
  try {
    await execPromise(`tmux kill-session -t "${req.params.name}"`);
    res.json({ success: true, message: `Session '${req.params.name}' killed` });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/sessions/:name/attach', async (req, res) => {
  try {
    // Generate attach command for user to run in terminal
    const attachCmd = `tmux attach-session -t "${req.params.name}"`;
    res.json({
      success: true,
      message: 'Run this command in your terminal',
      command: attachCmd
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.post('/api/sessions/:name/send-keys', async (req, res) => {
  const { keys } = req.body;
  try {
    await execPromise(`tmux send-keys -t "${req.params.name}" "${keys}" Enter`);
    res.json({ success: true, message: 'Keys sent' });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

app.get('/api/sessions/:name/capture', async (req, res) => {
  try {
    const { stdout } = await execPromise(`tmux capture-pane -t "${req.params.name}" -p`);
    res.json({ success: true, output: stdout });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// WebSocket Connection
wss.on('connection', (ws) => {
  console.log('🔌 New WebSocket client connected');

  // Send initial session list
  getTmuxSessions().then(sessions => {
    ws.send(JSON.stringify({ type: 'sessions', data: sessions }));
  });

  // Heartbeat interval to keep connection alive
  const heartbeat = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
    }
  }, 30000);

  // Monitor tmux sessions every 2 seconds
  const monitor = setInterval(async () => {
    try {
      const sessions = await getTmuxSessions();
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'sessions', data: sessions }));
      }
    } catch (error) {
      console.error('Monitor error:', error);
    }
  }, 2000);

  ws.on('message', async (message) => {
    try {
      const data = JSON.parse(message);
      console.log('📨 Received:', data);

      switch (data.action) {
        case 'get_sessions':
          const sessions = await getTmuxSessions();
          ws.send(JSON.stringify({ type: 'sessions', data: sessions }));
          break;

        case 'get_session_details':
          const windows = await getSessionDetails(data.session);
          ws.send(JSON.stringify({
            type: 'session_details',
            session: data.session,
            data: windows
          }));
          break;

        case 'create_session':
          await execPromise(`tmux new-session -d -s "${data.name}" -c "${data.path || '/home/jclee'}"`);
          ws.send(JSON.stringify({
            type: 'notification',
            level: 'success',
            message: `Session '${data.name}' created`
          }));
          break;

        case 'kill_session':
          await execPromise(`tmux kill-session -t "${data.session}"`);
          ws.send(JSON.stringify({
            type: 'notification',
            level: 'success',
            message: `Session '${data.session}' killed`
          }));
          break;

        case 'send_keys':
          await execPromise(`tmux send-keys -t "${data.session}" "${data.keys}" Enter`);
          ws.send(JSON.stringify({
            type: 'notification',
            level: 'info',
            message: 'Keys sent'
          }));
          break;

        case 'capture_pane':
          const { stdout } = await execPromise(`tmux capture-pane -t "${data.session}" -p`);
          ws.send(JSON.stringify({
            type: 'capture_output',
            session: data.session,
            output: stdout
          }));
          break;

        default:
          ws.send(JSON.stringify({
            type: 'error',
            message: `Unknown action: ${data.action}`
          }));
      }
    } catch (error) {
      ws.send(JSON.stringify({
        type: 'error',
        message: error.message
      }));
    }
  });

  ws.on('close', () => {
    console.log('🔌 WebSocket client disconnected');
    clearInterval(heartbeat);
    clearInterval(monitor);
  });
});

const PORT = process.env.PORT || 3333;
server.listen(PORT, () => {
  console.log(`🚀 Tmux Web Interface running on http://localhost:${PORT}`);
  console.log(`📡 WebSocket server ready`);
});
