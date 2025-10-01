#!/usr/bin/env node

import { TmuxWrapper } from '../src/tmux-wrapper.js';

/**
 * Test Tmux Wrapper functionality
 */
async function runTests() {
  console.log('🧪 Testing Tmux Wrapper\n');

  const tmux = new TmuxWrapper();
  const testSession = 'test-session-' + Date.now();

  try {
    // Test 1: Create session
    console.log('📝 Test 1: Create session');
    await tmux.createSession(testSession);
    console.log('✅ Session created\n');

    // Test 2: List sessions
    console.log('📝 Test 2: List sessions');
    const sessions = await tmux.listSessions();
    console.log(`✅ Found ${sessions.length} sessions`);
    console.log(sessions.map(s => `  - ${s.name}`).join('\n'));
    console.log();

    // Test 3: Execute command
    console.log('📝 Test 3: Execute command');
    await tmux.execCommand(testSession, 'echo "Hello from tmux!"');
    await tmux.execCommand(testSession, 'date');
    await tmux.execCommand(testSession, 'pwd');
    console.log('✅ Commands executed\n');

    // Wait a bit for output
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Test 4: Capture output
    console.log('📝 Test 4: Capture output');
    const output = await tmux.captureOutput(testSession, 20);
    console.log('✅ Output captured:');
    console.log('─'.repeat(60));
    console.log(output);
    console.log('─'.repeat(60));
    console.log();

    // Test 5: Get session info
    console.log('📝 Test 5: Get session info');
    const info = await tmux.getSessionInfo(testSession);
    console.log('✅ Session info:');
    console.log(`  Name: ${info.name}`);
    console.log(`  Windows: ${info.windows}`);
    console.log(`  Attached: ${info.attached}`);
    console.log(`  Created: ${info.created.toLocaleString()}\n`);

    // Test 6: Stream output
    console.log('📝 Test 6: Stream output (5 seconds)');
    const stream = tmux.streamOutput(testSession, 500);
    let streamCount = 0;

    const stopStream = stream.start((output, error) => {
      if (error) {
        console.log('❌ Stream error:', error.message);
        return;
      }
      streamCount++;
      if (streamCount <= 3) {
        console.log(`  [Stream ${streamCount}] Output received`);
      }
    });

    // Stream for 5 seconds
    await new Promise(resolve => setTimeout(resolve, 5000));
    stopStream();
    console.log(`✅ Streaming stopped (received ${streamCount} updates)\n`);

    // Test 7: Send special keys
    console.log('📝 Test 7: Send Ctrl+C');
    await tmux.sendKeys(testSession, 'C-c');
    console.log('✅ Ctrl+C sent\n');

    // Cleanup
    console.log('🧹 Cleanup: Kill test session');
    await tmux.killSession(testSession);
    console.log('✅ Session killed\n');

    console.log('🎉 All tests passed!');
    process.exit(0);

  } catch (error) {
    console.error('❌ Test failed:', error.message);

    // Cleanup on error
    try {
      await tmux.killSession(testSession);
      console.log('🧹 Cleanup: Session killed');
    } catch (e) {
      // Ignore cleanup errors
    }

    process.exit(1);
  }
}

runTests();
