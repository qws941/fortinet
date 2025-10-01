import { exec, spawn } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Tmux API Wrapper
 * Provides high-level interface to tmux commands
 */
export class TmuxWrapper {
  constructor(socketDir = '/home/jclee/.tmux/sockets') {
    this.socketDir = socketDir;
  }

  /**
   * Get socket path for session
   */
  getSocketPath(sessionName) {
    return `${this.socketDir}/${sessionName}`;
  }

  /**
   * List all tmux sessions
   */
  async listSessions() {
    try {
      const { stdout } = await execAsync(
        'tmux list-sessions -F "#{session_name}:#{session_created}:#{session_attached}"'
      );

      return stdout
        .trim()
        .split('\n')
        .filter(line => line)
        .map(line => {
          const [name, created, attached] = line.split(':');
          return {
            name,
            created: new Date(parseInt(created) * 1000),
            attached: attached === '1',
          };
        });
    } catch (error) {
      if (error.message.includes('no server running')) {
        return [];
      }
      throw error;
    }
  }

  /**
   * Create new tmux session
   */
  async createSession(sessionName, workingDir = process.cwd()) {
    const socketPath = this.getSocketPath(sessionName);
    const cmd = `tmux -S ${socketPath} new-session -d -s ${sessionName} -c "${workingDir}"`;

    try {
      await execAsync(cmd);
      return { success: true, session: sessionName };
    } catch (error) {
      throw new Error(`Failed to create session: ${error.message}`);
    }
  }

  /**
   * Kill tmux session
   */
  async killSession(sessionName) {
    const socketPath = this.getSocketPath(sessionName);
    const cmd = `tmux -S ${socketPath} kill-session -t ${sessionName}`;

    try {
      await execAsync(cmd);
      return { success: true, session: sessionName };
    } catch (error) {
      throw new Error(`Failed to kill session: ${error.message}`);
    }
  }

  /**
   * Execute command in tmux session
   */
  async execCommand(sessionName, command) {
    const socketPath = this.getSocketPath(sessionName);
    const cmd = `tmux -S ${socketPath} send-keys -t ${sessionName} "${command.replace(/"/g, '\\"')}" Enter`;

    try {
      await execAsync(cmd);
      return { success: true, command };
    } catch (error) {
      throw new Error(`Failed to execute command: ${error.message}`);
    }
  }

  /**
   * Capture pane output
   */
  async captureOutput(sessionName, lines = 100) {
    const socketPath = this.getSocketPath(sessionName);
    const cmd = `tmux -S ${socketPath} capture-pane -t ${sessionName} -p -S -${lines}`;

    try {
      const { stdout } = await execAsync(cmd);
      return stdout;
    } catch (error) {
      throw new Error(`Failed to capture output: ${error.message}`);
    }
  }

  /**
   * Send special keys (Ctrl-C, Enter, etc.)
   */
  async sendKeys(sessionName, keys) {
    const socketPath = this.getSocketPath(sessionName);
    const cmd = `tmux -S ${socketPath} send-keys -t ${sessionName} ${keys}`;

    try {
      await execAsync(cmd);
      return { success: true, keys };
    } catch (error) {
      throw new Error(`Failed to send keys: ${error.message}`);
    }
  }

  /**
   * Get session info
   */
  async getSessionInfo(sessionName) {
    const socketPath = this.getSocketPath(sessionName);
    try {
      const { stdout } = await execAsync(
        `tmux -S ${socketPath} list-sessions -F "#{session_name}:#{session_windows}:#{session_created}:#{session_attached}" | grep "^${sessionName}:"`
      );

      const [name, windows, created, attached] = stdout.trim().split(':');

      return {
        name,
        windows: parseInt(windows, 10),
        created: new Date(parseInt(created) * 1000),
        attached: attached === '1',
      };
    } catch (error) {
      throw new Error(`Session not found: ${sessionName}`);
    }
  }

  /**
   * Stream output continuously
   * Returns a readable stream
   */
  streamOutput(sessionName, intervalMs = 1000) {
    const socketPath = this.getSocketPath(sessionName);
    let lastOutput = '';

    return {
      start: (callback) => {
        const interval = setInterval(async () => {
          try {
            const output = await this.captureOutput(sessionName, 50);
            if (output !== lastOutput) {
              callback(output);
              lastOutput = output;
            }
          } catch (error) {
            clearInterval(interval);
            callback(null, error);
          }
        }, intervalMs);

        return () => clearInterval(interval);
      }
    };
  }
}
