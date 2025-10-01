import { App } from '@slack/bolt';
import { TmuxWrapper } from './tmux-wrapper.js';

/**
 * Slack Bot Handler
 * Handles /tmux slash commands
 */
export class SlackBot {
  constructor(config, tmuxSocketDir) {
    this.app = new App({
      token: config.slack.botToken,
      signingSecret: config.slack.signingSecret,
      socketMode: true,
      appToken: config.slack.appToken,
    });

    this.tmux = new TmuxWrapper(tmuxSocketDir);
    this.setupCommands();
  }

  setupCommands() {
    // Main /tmux command
    this.app.command('/tmux', async ({ command, ack, respond }) => {
      await ack();

      try {
        const response = await this.handleTmuxCommand(command.text);
        await respond(response);
      } catch (error) {
        await respond({
          response_type: 'ephemeral',
          text: `❌ Error: ${error.message}`,
        });
      }
    });

    // Event listeners
    this.app.event('app_mention', async ({ event, say }) => {
      await say({
        text: `👋 Hi <@${event.user}>! Use \`/tmux help\` to see available commands.`,
      });
    });

    console.log('✅ Slack Bot commands registered');
  }

  async handleTmuxCommand(text) {
    const [subcommand, ...args] = text.trim().split(/\s+/);

    switch (subcommand) {
      case 'list':
        return await this.handleList();

      case 'create':
        return await this.handleCreate(args[0]);

      case 'kill':
        return await this.handleKill(args[0]);

      case 'exec':
        return await this.handleExec(args[0], args.slice(1).join(' '));

      case 'output':
        return await this.handleOutput(args[0], parseInt(args[1]) || 50);

      case 'info':
        return await this.handleInfo(args[0]);

      case 'help':
        return this.getHelpMessage();

      default:
        return {
          response_type: 'ephemeral',
          text: `❓ Unknown command: \`${subcommand}\`\n\nUse \`/tmux help\` to see available commands.`,
        };
    }
  }

  async handleList() {
    const sessions = await this.tmux.listSessions();

    if (sessions.length === 0) {
      return {
        response_type: 'in_channel',
        text: '📋 No active tmux sessions',
      };
    }

    const blocks = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: '📋 Active Tmux Sessions',
        },
      },
      {
        type: 'divider',
      },
    ];

    sessions.forEach(session => {
      blocks.push({
        type: 'section',
        fields: [
          {
            type: 'mrkdwn',
            text: `*Name:*\n\`${session.name}\``,
          },
          {
            type: 'mrkdwn',
            text: `*Status:*\n${session.attached ? '🟢 Attached' : '⚪ Detached'}`,
          },
          {
            type: 'mrkdwn',
            text: `*Created:*\n${session.created.toLocaleString()}`,
          },
        ],
      });
      blocks.push({ type: 'divider' });
    });

    return {
      response_type: 'in_channel',
      blocks,
    };
  }

  async handleCreate(sessionName) {
    if (!sessionName) {
      return {
        response_type: 'ephemeral',
        text: '❌ Usage: `/tmux create <session-name>`',
      };
    }

    await this.tmux.createSession(sessionName);

    return {
      response_type: 'in_channel',
      text: `✅ Created session: \`${sessionName}\``,
    };
  }

  async handleKill(sessionName) {
    if (!sessionName) {
      return {
        response_type: 'ephemeral',
        text: '❌ Usage: `/tmux kill <session-name>`',
      };
    }

    await this.tmux.killSession(sessionName);

    return {
      response_type: 'in_channel',
      text: `🗑️  Killed session: \`${sessionName}\``,
    };
  }

  async handleExec(sessionName, command) {
    if (!sessionName || !command) {
      return {
        response_type: 'ephemeral',
        text: '❌ Usage: `/tmux exec <session-name> <command>`',
      };
    }

    await this.tmux.execCommand(sessionName, command);

    return {
      response_type: 'in_channel',
      text: `▶️  Executed in \`${sessionName}\`:\n\`\`\`${command}\`\`\``,
    };
  }

  async handleOutput(sessionName, lines = 50) {
    if (!sessionName) {
      return {
        response_type: 'ephemeral',
        text: '❌ Usage: `/tmux output <session-name> [lines]`',
      };
    }

    const output = await this.tmux.captureOutput(sessionName, lines);

    return {
      response_type: 'in_channel',
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: `📺 Output from: ${sessionName}`,
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: `\`\`\`${output}\`\`\``,
          },
        },
      ],
    };
  }

  async handleInfo(sessionName) {
    if (!sessionName) {
      return {
        response_type: 'ephemeral',
        text: '❌ Usage: `/tmux info <session-name>`',
      };
    }

    const info = await this.tmux.getSessionInfo(sessionName);

    return {
      response_type: 'in_channel',
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: `ℹ️  Session Info: ${sessionName}`,
          },
        },
        {
          type: 'section',
          fields: [
            {
              type: 'mrkdwn',
              text: `*Name:*\n\`${info.name}\``,
            },
            {
              type: 'mrkdwn',
              text: `*Windows:*\n${info.windows}`,
            },
            {
              type: 'mrkdwn',
              text: `*Status:*\n${info.attached ? '🟢 Attached' : '⚪ Detached'}`,
            },
            {
              type: 'mrkdwn',
              text: `*Created:*\n${info.created.toLocaleString()}`,
            },
          ],
        },
      ],
    };
  }

  getHelpMessage() {
    return {
      response_type: 'ephemeral',
      blocks: [
        {
          type: 'header',
          text: {
            type: 'plain_text',
            text: '📖 Tmux Bridge Commands',
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: '*Available Commands:*',
          },
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: [
              '`/tmux list` - List all sessions',
              '`/tmux create <name>` - Create new session',
              '`/tmux kill <name>` - Kill session',
              '`/tmux exec <name> <cmd>` - Execute command',
              '`/tmux output <name> [lines]` - Get output',
              '`/tmux info <name>` - Session info',
              '`/tmux help` - Show this help',
            ].join('\n'),
          },
        },
        {
          type: 'divider',
        },
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: '*WebSocket API:*\n`ws://localhost:3001`\n\nFor real-time streaming, connect via WebSocket.',
          },
        },
      ],
    };
  }

  async start() {
    await this.app.start();
    console.log('⚡ Slack Bot is running!');
  }

  async stop() {
    await this.app.stop();
    console.log('🛑 Slack Bot stopped');
  }
}
