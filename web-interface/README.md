# Tmux 웹 인터페이스 (WebSocket)

실시간 tmux 세션 관리를 위한 WebSocket 기반 웹 인터페이스

## 🚀 기능

- ✅ **실시간 세션 모니터링** - WebSocket으로 5초마다 자동 업데이트
- ✅ **세션 생성/삭제** - 웹에서 직접 세션 관리
- ✅ **TS 데이터베이스 통합** - TS 명령어 시스템과 완전 통합
- ✅ **아름다운 UI** - 반응형 그라데이션 디자인
- ✅ **REST API 제공** - 프로그래밍 방식 접근 가능

## 📦 설치

```bash
cd /home/jclee/app/tmux/web-interface
npm install
```

## 🎮 실행

### 개발 모드 (자동 재시작)
```bash
npm run dev
```

### 프로덕션 모드
```bash
npm start
```

기본 포트: **3030**

## 🌐 접속

- **웹 UI**: http://localhost:3030
- **WebSocket**: ws://localhost:3030
- **REST API**: http://localhost:3030/api
- **Health Check**: http://localhost:3030/health

## 🔌 WebSocket API

### 연결
```javascript
const ws = new WebSocket('ws://localhost:3030');
```

### 메시지 형식

#### 클라이언트 → 서버
```json
{
  "action": "list|create|kill|clean|sync",
  "name": "세션이름",
  "path": "/작업/경로"
}
```

#### 서버 → 클라이언트
```json
{
  "type": "sessions|success|error",
  "data": [...],
  "message": "메시지",
  "timestamp": "2025-10-01T19:40:00.000Z"
}
```

### 예제

```javascript
// 세션 목록 요청
ws.send(JSON.stringify({ action: 'list' }));

// 세션 생성
ws.send(JSON.stringify({
  action: 'create',
  name: 'my-project',
  path: '/home/jclee/app/my-project'
}));

// 세션 종료
ws.send(JSON.stringify({
  action: 'kill',
  sessionName: 'my-project'
}));
```

## 🛠️ REST API

### GET /api/sessions
모든 세션 목록 조회

```bash
curl http://localhost:3030/api/sessions
```

### POST /api/sessions/create
새 세션 생성

```bash
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "path": "/tmp"}'
```

### DELETE /api/sessions/:name
세션 삭제

```bash
curl -X DELETE http://localhost:3030/api/sessions/test
```

## 🎨 웹 UI 기능

1. **세션 카드 뷰**: 모든 활성 세션을 카드로 표시
2. **실시간 업데이트**: WebSocket으로 5초마다 자동 갱신
3. **상태 표시**: 연결됨/분리됨 상태 시각화
4. **원클릭 액션**: 새로고침, 동기화, 정리, 생성
5. **세션 정보**: 창 개수, 생성 시간, 경로 등

## 🔧 설정

### 포트 변경
```bash
PORT=8080 npm start
```

### TS 데이터베이스 위치
기본값: `~/.config/ts/sessions.db`

## 🐳 Docker 실행 (선택)

```bash
# Dockerfile 생성
cat > Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3030
CMD ["npm", "start"]
EOF

# 빌드 & 실행
docker build -t tmux-web .
docker run -d -p 3030:3030 \
  -v ~/.config/ts:/root/.config/ts \
  -v ~/.tmux:/root/.tmux \
  --name tmux-web \
  tmux-web
```

## 📊 Grafana 통합

이 웹 인터페이스는 자동으로 TS 명령어 시스템과 통합되며,
모든 작업은 Grafana Loki에 로깅됩니다.

```bash
# Grafana에서 로그 확인
{job="ts-command"} |~ "web-interface"
```

## 🚨 문제 해결

### WebSocket 연결 실패
```bash
# 포트 충돌 확인
lsof -i :3030

# 방화벽 확인
sudo ufw allow 3030
```

### 세션 정보 불일치
```bash
# TS 데이터베이스 동기화
ts sync
```

## 📝 라이선스

MIT License

## 👨‍💻 개발자

jclee - Claude Code AI Assistant
