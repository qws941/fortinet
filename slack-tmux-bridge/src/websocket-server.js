import { WebSocketServer } from 'ws';
import { TmuxWrapper } from './tmux-wrapper.js';

/**
 * WebSocket Server for real-time tmux output streaming
 */
export class TmuxWebSocketServer {
  constructor(port, tmuxSocketDir) {
    this.wss = new WebSocketServer({ port });
    this.tmux = new TmuxWrapper(tmuxSocketDir);
    this.subscriptions = new Map(); // clientId -> { ws, session, stopStreaming }

    this.setupServer();
  }

  setupServer() {
    this.wss.on('connection', (ws) => {
      const clientId = this.generateClientId();
      console.log(`🔌 WebSocket client connected: ${clientId}`);

      ws.on('message', async (data) => {
        try {
          const message = JSON.parse(data.toString());
          await this.handleMessage(clientId, ws, message);
        } catch (error) {
          this.sendError(ws, error.message);
        }
      });

      ws.on('close', () => {
        console.log(`🔌 WebSocket client disconnected: ${clientId}`);
        this.unsubscribe(clientId);
      });

      ws.on('error', (error) => {
        console.error(`❌ WebSocket error for ${clientId}:`, error);
        this.unsubscribe(clientId);
      });

      // Send welcome message
      this.send(ws, {
        type: 'connected',
        clientId,
        timestamp: new Date().toISOString(),
      });
    });

    console.log(`🚀 WebSocket server listening on port ${this.wss.options.port}`);
  }

  async handleMessage(clientId, ws, message) {
    const { action, session, command, keys, lines } = message;

    switch (action) {
      case 'subscribe':
        await this.subscribe(clientId, ws, session);
        break;

      case 'unsubscribe':
        this.unsubscribe(clientId);
        break;

      case 'exec':
        await this.execCommand(ws, session, command);
        break;

      case 'sendKeys':
        await this.sendKeys(ws, session, keys);
        break;

      case 'capture':
        await this.captureOutput(ws, session, lines);
        break;

      case 'list':
        await this.listSessions(ws);
        break;

      case 'create':
        await this.createSession(ws, session);
        break;

      case 'kill':
        await this.killSession(ws, session);
        break;

      default:
        this.sendError(ws, `Unknown action: ${action}`);
    }
  }

  async subscribe(clientId, ws, session) {
    // Unsubscribe from previous session if any
    this.unsubscribe(clientId);

    // Start streaming output
    const stream = this.tmux.streamOutput(session, 500);
    const stopStreaming = stream.start((output, error) => {
      if (error) {
        this.sendError(ws, `Stream error: ${error.message}`);
        this.unsubscribe(clientId);
        return;
      }

      this.send(ws, {
        type: 'output',
        session,
        data: output,
        timestamp: new Date().toISOString(),
      });
    });

    this.subscriptions.set(clientId, { ws, session, stopStreaming });

    this.send(ws, {
      type: 'subscribed',
      session,
      timestamp: new Date().toISOString(),
    });

    console.log(`📡 Client ${clientId} subscribed to session: ${session}`);
  }

  unsubscribe(clientId) {
    const subscription = this.subscriptions.get(clientId);
    if (subscription) {
      subscription.stopStreaming();
      this.subscriptions.delete(clientId);
      console.log(`📡 Client ${clientId} unsubscribed`);
    }
  }

  async execCommand(ws, session, command) {
    try {
      const result = await this.tmux.execCommand(session, command);
      this.send(ws, {
        type: 'exec_result',
        session,
        command,
        success: true,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  async sendKeys(ws, session, keys) {
    try {
      await this.tmux.sendKeys(session, keys);
      this.send(ws, {
        type: 'keys_sent',
        session,
        keys,
        success: true,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  async captureOutput(ws, session, lines = 100) {
    try {
      const output = await this.tmux.captureOutput(session, lines);
      this.send(ws, {
        type: 'capture_result',
        session,
        data: output,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  async listSessions(ws) {
    try {
      const sessions = await this.tmux.listSessions();
      this.send(ws, {
        type: 'session_list',
        sessions,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  async createSession(ws, session) {
    try {
      const result = await this.tmux.createSession(session);
      this.send(ws, {
        type: 'session_created',
        session,
        success: true,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  async killSession(ws, session) {
    try {
      await this.tmux.killSession(session);
      this.send(ws, {
        type: 'session_killed',
        session,
        success: true,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      this.sendError(ws, error.message);
    }
  }

  send(ws, data) {
    if (ws.readyState === ws.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  sendError(ws, message) {
    this.send(ws, {
      type: 'error',
      error: message,
      timestamp: new Date().toISOString(),
    });
  }

  generateClientId() {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  close() {
    // Clean up all subscriptions
    for (const [clientId, subscription] of this.subscriptions) {
      subscription.stopStreaming();
    }
    this.subscriptions.clear();

    // Close WebSocket server
    this.wss.close();
    console.log('🛑 WebSocket server closed');
  }
}
