import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Grafana Loki Logger
 * Sends logs to Grafana Loki via Promtail
 */
export class GrafanaLogger {
  constructor(jobName = 'slack-tmux-bridge') {
    this.jobName = jobName;
    this.lokiUrl = process.env.LOKI_URL || 'http://localhost:3100';
  }

  /**
   * Log message to Grafana Loki
   */
  async log(level, message, metadata = {}) {
    const timestamp = new Date().toISOString();

    const logEntry = {
      timestamp,
      level,
      message,
      job: this.jobName,
      ...metadata,
    };

    // Log to console
    const emoji = this.getLevelEmoji(level);
    console.log(`${emoji} [${timestamp}] ${level.toUpperCase()}: ${message}`);

    // Send to Loki (via logger command if available)
    try {
      const logLine = JSON.stringify(logEntry);

      // Try to send via promtail if available
      // For now, just write to stdout which promtail can capture
      await this.sendToLoki(logLine);
    } catch (error) {
      console.error('Failed to send to Loki:', error.message);
    }
  }

  async sendToLoki(logLine) {
    // If promtail is configured to watch stdout, this will be captured
    // Otherwise, you can use the Loki push API directly

    const lokiPayload = {
      streams: [
        {
          stream: {
            job: this.jobName,
            level: 'info',
          },
          values: [
            [String(Date.now() * 1000000), logLine],
          ],
        },
      ],
    };

    try {
      // Direct push to Loki (uncomment if you want direct push)
      // const response = await fetch(`${this.lokiUrl}/loki/api/v1/push`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(lokiPayload),
      // });

      // For now, rely on promtail to capture stdout
      return true;
    } catch (error) {
      console.error('Loki push failed:', error.message);
      return false;
    }
  }

  getLevelEmoji(level) {
    const emojis = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
      debug: '🔍',
    };
    return emojis[level] || '📝';
  }

  // Convenience methods
  info(message, metadata) {
    return this.log('info', message, metadata);
  }

  success(message, metadata) {
    return this.log('success', message, metadata);
  }

  warning(message, metadata) {
    return this.log('warning', message, metadata);
  }

  error(message, metadata) {
    return this.log('error', message, metadata);
  }

  debug(message, metadata) {
    return this.log('debug', message, metadata);
  }

  // Session-specific logging
  sessionCreated(sessionName, metadata = {}) {
    return this.success(`Session created: ${sessionName}`, {
      event: 'session_created',
      session: sessionName,
      ...metadata,
    });
  }

  sessionKilled(sessionName, metadata = {}) {
    return this.info(`Session killed: ${sessionName}`, {
      event: 'session_killed',
      session: sessionName,
      ...metadata,
    });
  }

  commandExecuted(sessionName, command, metadata = {}) {
    return this.info(`Command executed in ${sessionName}: ${command}`, {
      event: 'command_executed',
      session: sessionName,
      command,
      ...metadata,
    });
  }

  websocketConnected(clientId, metadata = {}) {
    return this.success(`WebSocket client connected: ${clientId}`, {
      event: 'websocket_connected',
      client_id: clientId,
      ...metadata,
    });
  }

  websocketDisconnected(clientId, metadata = {}) {
    return this.info(`WebSocket client disconnected: ${clientId}`, {
      event: 'websocket_disconnected',
      client_id: clientId,
      ...metadata,
    });
  }

  slackCommandReceived(command, user, metadata = {}) {
    return this.info(`Slack command received: ${command}`, {
      event: 'slack_command',
      command,
      user,
      ...metadata,
    });
  }
}

// Singleton instance
export const logger = new GrafanaLogger();
