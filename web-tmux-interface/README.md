# Tmux Web Interface

WebSocket 기반 실시간 Tmux 세션 관리 웹 인터페이스

## 기능

- ✅ 실시간 세션 모니터링 (WebSocket)
- ✅ 세션 생성/삭제/조회
- ✅ 세션 검색 및 필터링
- ✅ 명령어 전송
- ✅ Pane 캡처 및 출력 보기
- ✅ 반응형 UI (모바일/데스크톱)
- ✅ 자동 재연결

## 설치 및 실행

```bash
cd /home/jclee/app/tmux/web-tmux-interface

# 의존성 설치
npm install

# 서버 시작
npm start

# 개발 모드 (nodemon)
npm run dev
```

## 접속

웹 브라우저에서:
```
http://localhost:3333
```

## API 엔드포인트

### REST API

- `GET /api/sessions` - 모든 세션 조회
- `GET /api/sessions/:name` - 특정 세션 상세 조회
- `POST /api/sessions` - 새 세션 생성
- `DELETE /api/sessions/:name` - 세션 삭제
- `POST /api/sessions/:name/send-keys` - 명령어 전송
- `GET /api/sessions/:name/capture` - Pane 캡처

### WebSocket 메시지

```javascript
// 서버로 전송
{
  "action": "get_sessions" | "create_session" | "kill_session" | "send_keys" | "capture_pane",
  "session": "세션이름",
  "name": "새세션이름",
  "path": "/경로",
  "keys": "명령어"
}

// 서버로부터 수신
{
  "type": "sessions" | "notification" | "capture_output" | "error",
  "data": [...],
  "message": "메시지",
  "level": "success" | "error" | "info"
}
```

## 백그라운드 실행

```bash
# tmux 세션으로 실행
tmux new -s tmux-web -d "cd /home/jclee/app/tmux/web-tmux-interface && npm start"

# 또는 nohup
nohup npm start > /tmp/tmux-web.log 2>&1 &
```

## 문제 해결

### 포트 충돌
기본 포트 3333이 사용 중이면:
```bash
PORT=4444 npm start
```

### WebSocket 연결 실패
- 방화벽 확인
- CORS 설정 확인
- 브라우저 콘솔에서 에러 확인

## 보안 주의사항

⚠️ 이 인터페이스는 로컬 개발 환경용입니다.
프로덕션 환경에서 사용하려면:
- 인증/인가 추가
- HTTPS 사용
- Rate limiting 추가
- 입력 검증 강화
