#!/usr/bin/env node
/**
 * WebSocket 테스트 클라이언트
 */

const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:3030');

ws.on('open', () => {
  console.log('✅ WebSocket 연결 성공');

  // 세션 목록 요청
  console.log('\n📡 세션 목록 요청 중...');
  ws.send(JSON.stringify({ action: 'list' }));

  // 5초 후 자동 종료
  setTimeout(() => {
    console.log('\n👋 연결 종료');
    ws.close();
    process.exit(0);
  }, 5000);
});

ws.on('message', (data) => {
  const msg = JSON.parse(data);

  console.log('\n📨 서버로부터 메시지 수신:');
  console.log(`타입: ${msg.type}`);

  if (msg.type === 'sessions') {
    console.log(`\n🖥️ 활성 세션 (${msg.data.length}개):\n`);

    msg.data.forEach((session, idx) => {
      console.log(`${idx + 1}. ${session.name}`);
      console.log(`   상태: ${session.status === 'attached' ? '🟢 연결됨' : '⚪ 분리됨'}`);
      console.log(`   창: ${session.windows}개`);
      console.log(`   생성: ${new Date(session.created).toLocaleString('ko-KR')}`);
      if (session.hasMetadata && session.metadata.path) {
        console.log(`   경로: ${session.metadata.path}`);
      }
      console.log('');
    });
  } else if (msg.type === 'success') {
    console.log(`✅ ${msg.message}`);
  } else if (msg.type === 'error') {
    console.log(`❌ ${msg.message}`);
  }
});

ws.on('error', (error) => {
  console.error('❌ WebSocket 오류:', error.message);
  process.exit(1);
});

ws.on('close', () => {
  console.log('🔌 WebSocket 연결 종료');
});
