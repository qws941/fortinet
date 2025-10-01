# 🚀 빠른 시작 가이드

## 1단계: 즉시 실행

```bash
cd /home/jclee/app/tmux/web-interface
./deploy.sh
```

**모드 선택:**
- `1`: 로컬 Node.js 서버 (개발/테스트용)
- `2`: Systemd 서비스 (프로덕션, 자동 시작)
- `3`: Docker 컨테이너 (격리 환경)

## 2단계: 브라우저 접속

```
http://localhost:3030
```

## 3단계: 사용하기

### 웹 UI에서:
- ✅ **실시간 세션 목록** - 5초마다 자동 업데이트
- ✅ **세션 생성** - "➕ 세션 생성" 버튼 클릭
- ✅ **세션 종료** - 각 카드의 "❌ 종료" 버튼
- ✅ **동기화** - "🔗 동기화" 버튼으로 TS DB 동기화
- ✅ **전체 정리** - "🧹 모두 정리" 버튼

### 명령줄에서:

```bash
# REST API로 세션 목록 조회
curl http://localhost:3030/api/sessions | jq '.'

# 세션 생성
curl -X POST http://localhost:3030/api/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project", "path": "/home/jclee/app/my-project"}'

# 세션 종료
curl -X DELETE http://localhost:3030/api/sessions/my-project

# WebSocket 테스트
node test-websocket.js
```

## 📊 특징

### 실시간 모니터링
- WebSocket으로 실시간 세션 상태 업데이트
- 연결/분리 상태 시각화
- 프로젝트 경로 표시

### TS 명령어 통합
- TS 데이터베이스와 완전 통합
- 메타데이터 자동 동기화
- 소켓 파일 관리

### 예쁜 UI
- 반응형 그라데이션 디자인
- 카드 기반 레이아웃
- 호버 애니메이션

## 🔧 관리 명령어

### 로컬 서버
```bash
# 시작
npm start

# 개발 모드 (자동 재시작)
npm run dev

# 로그 확인
tail -f /tmp/tmux-web.log

# 중지
pkill -f "node.*server.js"
```

### Systemd 서비스
```bash
# 상태 확인
sudo systemctl status tmux-web

# 시작/중지/재시작
sudo systemctl start tmux-web
sudo systemctl stop tmux-web
sudo systemctl restart tmux-web

# 로그 확인
sudo journalctl -u tmux-web -f

# 자동 시작 활성화/비활성화
sudo systemctl enable tmux-web
sudo systemctl disable tmux-web
```

### Docker
```bash
# 빌드
docker build -t tmux-web-interface .

# 실행
docker-compose up -d

# 로그 확인
docker logs -f tmux-web-interface

# 중지
docker-compose down

# 상태 확인
docker ps | grep tmux-web-interface
```

## 🐛 문제 해결

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :3030

# 프로세스 종료
kill $(lsof -t -i:3030)
```

### WebSocket 연결 실패
```bash
# 서버 헬스 체크
curl http://localhost:3030/health

# 방화벽 확인
sudo ufw status
sudo ufw allow 3030
```

### 세션 정보 불일치
```bash
# TS 데이터베이스 동기화
ts sync

# 웹 UI에서 동기화 버튼 클릭
# 또는
curl -X POST http://localhost:3030/api/sync
```

## 📈 Grafana 통합

모든 작업은 자동으로 Grafana Loki에 로깅됩니다:

```
{job="ts-command"} |~ "web-interface"
```

## 🔒 보안

### 기본 설정 (로컬 전용)
- 현재 localhost에서만 접근 가능
- 인증 없음

### 외부 접근 시 (선택)
```bash
# Nginx 리버스 프록시 추천
# 예제 설정:

server {
  listen 80;
  server_name tmux.example.com;

  location / {
    proxy_pass http://localhost:3030;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
  }
}
```

## 📚 추가 문서

- [README.md](README.md) - 전체 문서
- [server.js](server.js) - 서버 소스 코드
- [public/index.html](public/index.html) - 웹 UI 소스

## 💡 팁

1. **여러 프로젝트 관리**: 각 프로젝트마다 세션 생성
2. **자동 시작**: Systemd 서비스 모드 사용
3. **원격 접근**: VPN + Nginx 리버스 프록시
4. **모니터링**: Grafana 대시보드 생성

---

**즐거운 코딩 되세요!** 🎉
