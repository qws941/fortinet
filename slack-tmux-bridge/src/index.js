#!/usr/bin/env node

import { config, validateConfig } from './config.js';
import { TmuxWebSocketServer } from './websocket-server.js';
import { SlackBot } from './slack-bot.js';

/**
 * Main Server
 * Integrates WebSocket server and Slack Bot
 */
class TmuxSlackBridge {
  constructor() {
    this.wsServer = null;
    this.slackBot = null;
  }

  async start() {
    console.log('🚀 Starting Tmux Slack Bridge...\n');

    // Validate configuration
    validateConfig();

    // Start WebSocket server
    console.log('📡 Starting WebSocket server...');
    this.wsServer = new TmuxWebSocketServer(
      config.server.wsPort,
      config.tmux.socketDir
    );

    // Start Slack Bot
    console.log('⚡ Starting Slack Bot...');
    this.slackBot = new SlackBot(config, config.tmux.socketDir);
    await this.slackBot.start();

    console.log('\n' + '='.repeat(60));
    console.log('✅ Tmux Slack Bridge is running!');
    console.log('='.repeat(60));
    console.log(`📡 WebSocket: ws://localhost:${config.server.wsPort}`);
    console.log(`⚡ Slack Bot: Ready for /tmux commands`);
    console.log(`📂 Tmux Sockets: ${config.tmux.socketDir}`);
    console.log('='.repeat(60) + '\n');

    // Graceful shutdown
    this.setupShutdownHandlers();
  }

  setupShutdownHandlers() {
    const shutdown = async (signal) => {
      console.log(`\n🛑 Received ${signal}, shutting down gracefully...`);

      if (this.slackBot) {
        await this.slackBot.stop();
      }

      if (this.wsServer) {
        this.wsServer.close();
      }

      console.log('👋 Goodbye!');
      process.exit(0);
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

    process.on('uncaughtException', (error) => {
      console.error('❌ Uncaught Exception:', error);
      shutdown('uncaughtException');
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
      shutdown('unhandledRejection');
    });
  }
}

// Start server
const bridge = new TmuxSlackBridge();
bridge.start().catch((error) => {
  console.error('❌ Failed to start server:', error);
  process.exit(1);
});
