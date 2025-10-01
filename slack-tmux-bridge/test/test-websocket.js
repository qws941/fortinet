#!/usr/bin/env node

import WebSocket from 'ws';

/**
 * Test WebSocket Server
 */
async function runTests() {
  console.log('🧪 Testing WebSocket Server\n');

  const wsUrl = process.env.WS_URL || 'ws://localhost:3001';
  const testSession = 'ws-test-' + Date.now();

  console.log(`🔌 Connecting to ${wsUrl}...`);

  const ws = new WebSocket(wsUrl);

  ws.on('open', () => {
    console.log('✅ Connected to WebSocket server\n');

    // Test 1: Create session
    console.log('📝 Test 1: Create session');
    ws.send(JSON.stringify({
      action: 'create',
      session: testSession,
    }));
  });

  ws.on('message', (data) => {
    const message = JSON.parse(data.toString());

    console.log(`📨 Received: ${message.type}`);

    if (message.type === 'session_created') {
      console.log(`✅ Session created: ${message.session}\n`);

      // Test 2: Execute command
      console.log('📝 Test 2: Execute command');
      ws.send(JSON.stringify({
        action: 'exec',
        session: testSession,
        command: 'echo "WebSocket test successful"',
      }));
    }

    if (message.type === 'exec_result') {
      console.log('✅ Command executed\n');

      // Test 3: Capture output
      console.log('📝 Test 3: Capture output');
      setTimeout(() => {
        ws.send(JSON.stringify({
          action: 'capture',
          session: testSession,
          lines: 10,
        }));
      }, 1000);
    }

    if (message.type === 'capture_result') {
      console.log('✅ Output captured:');
      console.log('─'.repeat(60));
      console.log(message.data);
      console.log('─'.repeat(60));
      console.log();

      // Test 4: Subscribe to stream
      console.log('📝 Test 4: Subscribe to stream');
      ws.send(JSON.stringify({
        action: 'subscribe',
        session: testSession,
      }));
    }

    if (message.type === 'subscribed') {
      console.log(`✅ Subscribed to ${message.session}\n`);

      // Send a command while streaming
      console.log('📝 Test 5: Execute while streaming');
      ws.send(JSON.stringify({
        action: 'exec',
        session: testSession,
        command: 'echo "This should appear in stream"',
      }));

      // Wait and then cleanup
      setTimeout(() => {
        console.log('\n🧹 Cleanup: Kill session');
        ws.send(JSON.stringify({
          action: 'kill',
          session: testSession,
        }));
      }, 3000);
    }

    if (message.type === 'output') {
      console.log('📺 Stream output received');
    }

    if (message.type === 'session_killed') {
      console.log(`✅ Session killed: ${message.session}\n`);
      console.log('🎉 All tests passed!');
      ws.close();
      process.exit(0);
    }

    if (message.type === 'error') {
      console.error(`❌ Error: ${message.error}`);
    }
  });

  ws.on('error', (error) => {
    console.error('❌ WebSocket error:', error.message);
    console.log('\n💡 Make sure the server is running: npm start');
    process.exit(1);
  });

  ws.on('close', () => {
    console.log('🔌 WebSocket connection closed');
  });

  // Timeout after 30 seconds
  setTimeout(() => {
    console.error('❌ Test timeout');
    ws.close();
    process.exit(1);
  }, 30000);
}

runTests();
